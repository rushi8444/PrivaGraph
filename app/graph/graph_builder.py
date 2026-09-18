"""NetworkX-based knowledge graph builder.

Constructs a directed multigraph from extracted triples.
Nodes carry metadata (entity_type, namespace, classification).
Edges carry metadata (predicate, source sentence, doc_id).
"""

from __future__ import annotations

from collections import Counter

import networkx as nx

from app.graph.triple_extractor import Triple
from app.models.document import OKFHeader
from app.models.graph import GraphData, GraphEdge, GraphNode, GraphStats


class GraphContaminationError(ValueError):
    """Raised when an entity accumulates an excessive number of edges indicating graph contamination."""
    pass


class KnowledgeGraphBuilder:
    """Builds and manages the in-memory knowledge graph."""

    MAX_EDGES_PER_ENTITY: int = 100

    def __init__(self, max_edges_per_entity: int = 100):
        self.graph = nx.MultiDiGraph()
        self.MAX_EDGES_PER_ENTITY = max_edges_per_entity

    def add_triples(self, triples: list[Triple], header: OKFHeader) -> None:
        """Add extracted triples to the knowledge graph.

        Enforces a circuit breaker threshold to abort ingestion if any entity
        accumulates an excessive number of edges (preventing cartesian explosions).

        Args:
            triples: List of SVO triples to add.
            header: OKF header with namespace and ACL metadata.

        Raises:
            GraphContaminationError: If any entity exceeds MAX_EDGES_PER_ENTITY.
        """
        for triple in triples:
            self._ensure_node(
                triple.subject,
                doc_id=triple.doc_id,
                namespace=header.graph.namespace,
                classification=header.document.classification.value,
            )
            self._ensure_node(
                triple.object,
                doc_id=triple.doc_id,
                namespace=header.graph.namespace,
                classification=header.document.classification.value,
            )
            # Check if identical edge already exists
            existing_edges = self.graph.get_edge_data(triple.subject, triple.object) or {}
            duplicate = any(
                data.get("predicate") == triple.predicate
                for data in existing_edges.values()
            )
            if not duplicate:
                # Circuit breaker check on entity edge count
                subject_edges = self.graph.out_degree(triple.subject) + self.graph.in_degree(triple.subject)
                if subject_edges >= self.MAX_EDGES_PER_ENTITY:
                    raise GraphContaminationError(
                        f"Graph contamination circuit breaker triggered: entity '{triple.subject}' reached "
                        f"{subject_edges} edges (limit: {self.MAX_EDGES_PER_ENTITY}). Ingestion halted."
                    )

                self.graph.add_edge(
                    triple.subject,
                    triple.object,
                    predicate=triple.predicate,
                    source_sentence=triple.source_sentence,
                    doc_id=triple.doc_id,
                    namespace=header.graph.namespace,
                )

    def _ensure_node(self, node_id: str, **attrs) -> None:
        """Add node if not exists; merge metadata if exists."""
        if self.graph.has_node(node_id):
            existing = self.graph.nodes[node_id]
            doc_ids = set(existing.get("doc_ids", []))
            doc_ids.add(attrs.get("doc_id", ""))
            existing["doc_ids"] = list(doc_ids)
        else:
            doc_id = attrs.pop("doc_id", "")
            attrs["doc_ids"] = [doc_id] if doc_id else []
            self.graph.add_node(node_id, **attrs)

    def get_neighbors(self, node_id: str, depth: int = 2) -> nx.MultiDiGraph:
        """Extract a subgraph around a node using BFS up to `depth` hops.

        Args:
            node_id: The center node to expand from.
            depth: Maximum traversal depth.

        Returns:
            Subgraph containing all reachable nodes within depth.
        """
        if node_id not in self.graph:
            return nx.MultiDiGraph()

        visited: set[str] = set()
        frontier: set[str] = {node_id}

        for _ in range(depth):
            next_frontier: set[str] = set()
            for n in frontier:
                if n not in visited:
                    visited.add(n)
                    next_frontier.update(self.graph.successors(n))
                    next_frontier.update(self.graph.predecessors(n))
            frontier = next_frontier - visited

        visited.update(frontier)
        return self.graph.subgraph(visited).copy()

    def serialize_subgraph(self, subgraph: nx.MultiDiGraph) -> str:
        """Serialize subgraph to a text format suitable for LLM context.

        Args:
            subgraph: The subgraph to serialize.

        Returns:
            Markdown-formatted string for LLM context injection.
        """
        lines = ["# Knowledge Graph Context", ""]
        lines.append("## Entities")
        for node, data in subgraph.nodes(data=True):
            ns = data.get("namespace", "unknown")
            lines.append(f"- {node} (namespace: {ns})")

        lines.append("")
        lines.append("## Relationships")
        for u, v, data in subgraph.edges(data=True):
            pred = data.get("predicate", "RELATED")
            lines.append(f"- {u} --[{pred}]--> {v}")

        return "\n".join(lines)

    def to_graph_data(self) -> GraphData:
        """Export the full graph as API-serializable GraphData."""
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            nodes.append(
                GraphNode(
                    id=node_id,
                    entity_type=data.get("entity_type"),
                    namespace=data.get("namespace", ""),
                    classification=data.get("classification", ""),
                    doc_ids=data.get("doc_ids", []),
                    label=node_id,
                )
            )

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append(
                GraphEdge(
                    source=u,
                    target=v,
                    predicate=data.get("predicate", "RELATED"),
                    source_sentence=data.get("source_sentence", ""),
                    doc_id=data.get("doc_id", ""),
                    namespace=data.get("namespace", ""),
                )
            )

        return GraphData(nodes=nodes, edges=edges)

    def get_stats(self) -> GraphStats:
        """Return summary statistics about the graph."""
        entity_types: Counter[str] = Counter()
        namespaces: set[str] = set()

        for _, data in self.graph.nodes(data=True):
            et = data.get("entity_type")
            if et:
                entity_types[et] += 1
            ns = data.get("namespace")
            if ns:
                namespaces.add(ns)

        return GraphStats(
            total_nodes=self.graph.number_of_nodes(),
            total_edges=self.graph.number_of_edges(),
            namespaces=sorted(namespaces),
            entity_types=dict(entity_types),
        )

    def remove_document(self, doc_id: str) -> dict[str, int]:
        """Remove all edges and isolated nodes associated with a document.

        Args:
            doc_id: The document identifier to remove.

        Returns:
            Dict containing count of edges and nodes removed.
        """
        # 1. Collect and remove edges belonging to this document
        edges_to_remove = [
            (u, v, k)
            for u, v, k, data in self.graph.edges(data=True, keys=True)
            if data.get("doc_id") == doc_id
        ]
        for u, v, k in edges_to_remove:
            self.graph.remove_edge(u, v, key=k)

        # 2. Update nodes: remove doc_id from node metadata
        nodes_to_remove = []
        for node, data in list(self.graph.nodes(data=True)):
            doc_ids = data.get("doc_ids", [])
            if doc_id in doc_ids:
                doc_ids = [d for d in doc_ids if d != doc_id]
                data["doc_ids"] = doc_ids
            # If node has no remaining linked documents AND no connected edges, remove it
            if not doc_ids and self.graph.degree(node) == 0:
                nodes_to_remove.append(node)

        for node in nodes_to_remove:
            self.graph.remove_node(node)

        return {
            "edges_removed": len(edges_to_remove),
            "nodes_removed": len(nodes_to_remove),
        }

