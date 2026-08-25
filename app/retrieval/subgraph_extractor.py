"""Subgraph extractor module for extracting k-hop neighborhoods from the knowledge graph."""

from __future__ import annotations

import networkx as nx
from app.graph.graph_builder import KnowledgeGraphBuilder


class SubgraphExtractor:
    """Extracts k-hop subgraphs around seed nodes."""

    def __init__(self, graph_builder: KnowledgeGraphBuilder):
        self.graph_builder = graph_builder

    def extract_subgraph(self, seed_nodes: list[str], depth: int = 2) -> nx.MultiDiGraph:
        """Extract combined k-hop neighborhood around a set of seed nodes.

        Args:
            seed_nodes: Center node IDs.
            depth: Maximum traversal depth / hop distance.

        Returns:
            Combined directed MultiGraph containing the neighborhood.
        """
        combined = nx.MultiDiGraph()
        for node in seed_nodes:
            sub = self.graph_builder.get_neighbors(node, depth=depth)
            combined = nx.compose(combined, sub)
        return combined
