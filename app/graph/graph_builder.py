"""NetworkX-based knowledge graph builder.

Constructs a directed multigraph from extracted triples.
Nodes carry metadata (entity_type, namespace, ACL roles).
Edges carry metadata (predicate, source sentence, doc_id).
"""

from __future__ import annotations

from collections import Counter

import networkx as nx

from app.graph.triple_extractor import Triple
from app.models.document import OKFHeader
from app.models.graph import GraphData, GraphEdge, GraphNode, GraphStats


class KnowledgeGraphBuilder:
    """Builds and manages the in-memory knowledge graph."""

    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def add_triples(self, triples: list[Triple], header: OKFHeader) -> None:
        """Add extracted triples to the knowledge graph.

        Args:
            triples: List of SVO triples to add.
            header: OKF header with namespace and ACL metadata.
        """
        for triple in triples:
            self._ensure_node(
                triple.subject,
                doc_id=triple.doc_id,
                namespace=header.graph.namespace,
                classification=header.document.classification.value,
                allowed_roles=header.access_control.allowed_roles,
                denied_roles=header.access_control.denied_roles,
            )
            self._ensure_node(
                triple.object,
                doc_id=triple.doc_id,
                namespace=header.graph.namespace,
                classification=header.document.classification.value,
                allowed_roles=header.access_control.allowed_roles,
                denied_roles=header.access_control.denied_roles,
            )
            # Check if identical edge already exists
            existing_edges = self.graph.get_edge_data(triple.subject, triple.object) or {}
            duplicate = any(
                data.get("predicate") == triple.predicate
                for data in existing_edges.values()
            )
            if not duplicate:
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
                    allowed_roles=data.get("allowed_roles", []),
                    denied_roles=data.get("denied_roles", []),
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
