"""Graph-store abstraction: choose between JSON-file and Neo4j at startup."""
from __future__ import annotations

import networkx as nx
from typing import Iterable

from app.graph.triple_extractor import Triple
from app.models.document import OKFHeader


# ─────────────────────────── File-backed store ───────────────────────────────

class FileGraphStore:
    """Thin wrapper around the existing KnowledgeGraphBuilder — no behaviour change."""

    def __init__(self, persist_path):
        from app.graph.graph_builder import KnowledgeGraphBuilder
        self._b = KnowledgeGraphBuilder(persist_path=persist_path)

    # Proxy every attribute (graph, get_neighbors, serialize_subgraph, …) to the builder
    def __getattr__(self, name):
        return getattr(self._b, name)


# ─────────────────────────── Neo4j store ─────────────────────────────────────

_MERGE_TRIPLE = """
MERGE (s:Entity {id:$subj})
ON CREATE SET s.namespace=$ns, s.classification=$classification, s.doc_ids=[]
SET s.doc_ids = CASE WHEN $doc IN s.doc_ids THEN s.doc_ids ELSE s.doc_ids + $doc END
MERGE (o:Entity {id:$obj})
ON CREATE SET o.namespace=$ns, o.classification=$classification, o.doc_ids=[]
SET o.doc_ids = CASE WHEN $doc IN o.doc_ids THEN o.doc_ids ELSE o.doc_ids + $doc END
MERGE (s)-[r:REL {pred:$pred, doc_id:$doc}]->(o)
ON CREATE SET r.src=$src, r.namespace=$ns
"""

_BFS_QUERY = """
MATCH path=(n:Entity {id:$node_id})-[:REL*1..$MAX_DEPTH]-(m)
WHERE $docs = [] OR ALL(x IN relationships(path) WHERE x.doc_id IN $docs)
UNWIND nodes(path) AS nd
WITH DISTINCT nd
RETURN nd.id AS id, coalesce(nd.doc_ids,[]) AS doc_ids
"""


class Neo4jGraphStore:
    """Neo4j-backed graph store with the same public API as KnowledgeGraphBuilder."""

    def __init__(self, uri: str, user: str, password: str):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._ensure_index()
        # Build an in-memory NetworkX mirror so context_builder can use .graph directly
        self.graph = nx.MultiDiGraph()
        self._sync_from_neo4j()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _run(self, q: str, **p):
        with self.driver.session() as s:
            return list(s.run(q, p))

    def _ensure_index(self):
        self._run("CREATE INDEX entity_id IF NOT EXISTS FOR (n:Entity) ON (n.id)")

    def _sync_from_neo4j(self):
        """Re-populate the in-memory NetworkX graph from Neo4j (called at startup)."""
        self.graph.clear()
        for row in self._run("MATCH (n:Entity) RETURN n"):
            node = dict(row["n"])
            node_id = node.pop("id")
            self.graph.add_node(node_id, **node)
        for row in self._run("MATCH (s:Entity)-[r:REL]->(o:Entity) "
                              "RETURN s.id AS subj, o.id AS obj, r.pred AS pred, "
                              "r.src AS src, r.doc_id AS doc, r.namespace AS namespace"):
            self.graph.add_edge(row["subj"], row["obj"],
                                predicate=row["pred"],
                                source_sentence=row["src"],
                                doc_id=row["doc"],
                                namespace=row["namespace"])

    # ── public API ────────────────────────────────────────────────────────────

    def add_triples(self, triples: Iterable[Triple], header: OKFHeader):
        ns = header.graph.namespace
        for t in triples:
            self._run(_MERGE_TRIPLE, subj=t.subject, obj=t.object,
                      doc=t.doc_id, pred=t.predicate, src=t.source_sentence, ns=ns,
                      classification=header.document.classification.value)
            # Mirror into NetworkX so existing code using .graph still works
            for node_id in (t.subject, t.object):
                if not self.graph.has_node(node_id):
                    self.graph.add_node(node_id, namespace=ns,
                                        classification=header.document.classification.value,
                                        doc_ids=[])
                attrs = self.graph.nodes[node_id]
                if t.doc_id not in attrs.setdefault("doc_ids", []):
                    attrs["doc_ids"].append(t.doc_id)
            edge_data = self.graph.get_edge_data(t.subject, t.object) or {}
            if not any(data.get("predicate") == t.predicate
                       and data.get("doc_id") == t.doc_id
                       for data in edge_data.values()):
                self.graph.add_edge(t.subject, t.object, predicate=t.predicate,
                                    source_sentence=t.source_sentence, doc_id=t.doc_id,
                                    namespace=ns)

    def get_neighbors(self, node_id: str, depth: int = 2,
                      allowed_doc_ids=None) -> nx.MultiDiGraph:
        # Relationship range bounds are Cypher syntax, not bindable parameters.
        # Accept an integer and insert only that validated number in the query.
        depth = max(1, min(int(depth), 10))
        docs = list(allowed_doc_ids) if allowed_doc_ids else []
        query = _BFS_QUERY.replace("$MAX_DEPTH", str(depth))
        rows = self._run(query, node_id=node_id, docs=docs)
        node_ids = {r["id"] for r in rows}
        subgraph = self.graph.subgraph(node_ids).copy()
        if docs:
            allowed = set(docs)
            subgraph.remove_edges_from([
                (u, v, key) for u, v, key, data in subgraph.edges(keys=True, data=True)
                if data.get("doc_id") not in allowed
            ])
        return subgraph

    def clear(self):
        self._run("MATCH (n) DETACH DELETE n")
        self.graph.clear()

    def remove_document(self, doc_id: str) -> dict[str, int]:
        """Remove one document's graph edges and detach its nodes when unused."""
        before_edges = self.graph.number_of_edges()
        before_nodes = self.graph.number_of_nodes()
        self._run("MATCH ()-[r:REL {doc_id:$doc_id}]->() DELETE r", doc_id=doc_id)
        self._run("MATCH (n:Entity) WHERE $doc_id IN coalesce(n.doc_ids,[]) "
                  "SET n.doc_ids = [d IN n.doc_ids WHERE d <> $doc_id]", doc_id=doc_id)
        self._run("MATCH (n:Entity) WHERE size(coalesce(n.doc_ids,[])) = 0 "
                  "AND NOT (n)--() DELETE n")
        self._sync_from_neo4j()
        return {"edges_removed": before_edges - self.graph.number_of_edges(),
                "nodes_removed": before_nodes - self.graph.number_of_nodes()}

    def to_graph_data(self):
        from app.graph.graph_builder import KnowledgeGraphBuilder
        builder = KnowledgeGraphBuilder()
        builder.graph = self.graph
        return builder.to_graph_data()

    def get_stats(self):
        from app.graph.graph_builder import KnowledgeGraphBuilder
        builder = KnowledgeGraphBuilder()
        builder.graph = self.graph
        return builder.get_stats()

    def serialize_subgraph(self, subgraph: nx.MultiDiGraph) -> str:
        """Reuse the existing serializer from graph_builder."""
        from app.graph.graph_builder import KnowledgeGraphBuilder
        tmp = KnowledgeGraphBuilder()
        tmp.graph = subgraph
        return tmp.serialize_subgraph(subgraph)

    def save_to_disk(self):
        """Neo4j commits each write immediately; retained for API compatibility."""

    def close(self):
        self.driver.close()


