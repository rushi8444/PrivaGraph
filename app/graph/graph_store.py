"""Graph persistence layer.

Thin wrapper around KnowledgeGraphBuilder for future Neo4j migration.
MVP uses the in-memory NetworkX implementation directly.
"""

from __future__ import annotations

from app.graph.graph_builder import KnowledgeGraphBuilder


# For MVP, the graph store IS the graph builder.
# Phase 2 will abstract this behind a protocol to support Neo4j.
GraphStore = KnowledgeGraphBuilder
