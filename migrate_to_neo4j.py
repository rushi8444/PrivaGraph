"""Idempotently copy the JSON-backed graph to Neo4j without deleting existing data.

Run with ``python migrate_to_neo4j.py`` after starting the configured Neo4j service.
The source JSON graph is left untouched as a rollback copy.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase


def setting(name: str, default: str) -> str:
    """Read a setting from the process environment or this project's .env."""
    if name in os.environ:
        return os.environ[name]
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == name:
                return value.strip().strip("\"'")
    return default


NODE_BATCH = """
UNWIND $rows AS row
MERGE (n:Entity {id: row.id})
SET n += row.props
"""

EDGE_BATCH = """
UNWIND $rows AS row
MATCH (s:Entity {id: row.source})
MATCH (o:Entity {id: row.target})
MERGE (s)-[r:REL {pred: row.predicate, doc_id: row.doc_id}]->(o)
SET r += row.props
RETURN count(r) AS imported
"""


def neo4j_value(value: Any) -> Any:
    """Keep Neo4j-compatible scalar and homogeneous-list properties."""
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list) and all(
        item is None or isinstance(item, (str, bool, int, float)) for item in value
    ):
        return value
    return None


def batches(rows: list[dict], size: int):
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(setting("DATA_DIR", "data")) / "graph.json",
        help="NetworkX node-link JSON file (default: data/graph.json)",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    if not args.source.exists():
        parser.error(f"Graph file not found: {args.source}")

    data = json.loads(args.source.read_text(encoding="utf-8"))
    nodes = []
    for source_node in data.get("nodes", []):
        node_id = source_node.get("id")
        if node_id is None:
            raise ValueError("Every graph node must have an id")
        props = {key: neo4j_value(value) for key, value in source_node.items() if key != "id"}
        props = {key: value for key, value in props.items() if value is not None}
        nodes.append({"id": str(node_id), "props": props})

    edges = []
    for attrs in data.get("edges", []):
        source, target = attrs.get("source"), attrs.get("target")
        if source is None or target is None:
            raise ValueError("Every graph edge must have source and target ids")
        predicate = str(attrs.get("predicate", "RELATED"))
        doc_id = str(attrs.get("doc_id", ""))
        props = {key: neo4j_value(value) for key, value in attrs.items()
                 if key not in {"source", "target", "key"}}
        props.update({"pred": predicate, "doc_id": doc_id})
        props = {key: value for key, value in props.items() if value is not None}
        edges.append({
            "source": str(source),
            "target": str(target),
            "predicate": predicate,
            "doc_id": doc_id,
            "props": props,
        })

    with GraphDatabase.driver(
        setting("NEO4J_URI", "bolt://localhost:7687"),
        auth=(setting("NEO4J_USER", "neo4j"), setting("NEO4J_PASSWORD", "")),
    ) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            session.run(
                "CREATE INDEX entity_id IF NOT EXISTS FOR (n:Entity) ON (n.id)"
            ).consume()
            for batch in batches(nodes, args.batch_size):
                session.execute_write(lambda tx, rows=batch: tx.run(NODE_BATCH, rows=rows).consume())
            imported_edges = 0
            for batch in batches(edges, args.batch_size):
                result = session.execute_write(
                    lambda tx, rows=batch: tx.run(EDGE_BATCH, rows=rows).single()["imported"]
                )
                imported_edges += result

            node_count = session.run(
                "MATCH (n:Entity) WHERE n.id IN $ids RETURN count(DISTINCT n) AS count",
                ids=[node["id"] for node in nodes],
            ).single()["count"] if nodes else 0

    if node_count != len(nodes) or imported_edges != len(edges):
        raise RuntimeError(
            f"Migration verification failed: source {len(nodes)} nodes/{len(edges)} edges; "
            f"Neo4j matched {node_count} nodes/{imported_edges} edges."
        )

    print(
        f"Migration verified: {node_count} nodes and {imported_edges} relationships "
        f"imported from {args.source}. Existing Neo4j data and the source file were preserved."
    )


if __name__ == "__main__":
    main()
