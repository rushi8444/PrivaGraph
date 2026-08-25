"""Knowledge graph node and edge models."""

from __future__ import annotations

from pydantic import BaseModel


class GraphNode(BaseModel):
    """A node in the knowledge graph."""

    id: str
    entity_type: str | None = None
    namespace: str = ""
    classification: str = ""
    allowed_roles: list[str] = []
    denied_roles: list[str] = []
    doc_ids: list[str] = []
    label: str | None = None


class GraphEdge(BaseModel):
    """An edge (relationship) in the knowledge graph."""

    source: str
    target: str
    predicate: str
    source_sentence: str = ""
    doc_id: str = ""
    namespace: str = ""


class GraphData(BaseModel):
    """Serialized graph data for API responses."""

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class GraphStats(BaseModel):
    """Summary statistics for the knowledge graph."""

    total_nodes: int = 0
    total_edges: int = 0
    namespaces: list[str] = []
    entity_types: dict[str, int] = {}
