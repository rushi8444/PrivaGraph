"""Knowledge graph inspection API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import get_state

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/nodes")
async def get_graph_nodes():
    """Get all nodes and edges in the knowledge graph (tokenized)."""
    state = get_state()
    return state.graph_builder.to_graph_data().model_dump()


@router.get("/subgraph/{node_id}")
async def get_subgraph(node_id: str, depth: int = 2):
    """Get a subgraph around a specific node."""
    state = get_state()
    subgraph = state.graph_builder.get_neighbors(node_id, depth=depth)
    text = state.graph_builder.serialize_subgraph(subgraph)
    return {"node_id": node_id, "depth": depth, "context": text}


@router.get("/stats")
async def get_graph_stats():
    """Get summary statistics about the knowledge graph."""
    state = get_state()
    return state.graph_builder.get_stats().model_dump()
