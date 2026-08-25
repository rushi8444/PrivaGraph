"""Query request and response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """User query submitted to the privacy-preserving pipeline."""

    query: str
    model: str | None = None
    max_traversal_depth: int = Field(default=3, ge=1, le=10)
    include_graph_context: bool = False


class QueryMetadata(BaseModel):
    """Metadata about how a query was processed."""

    entities_reconstructed: int = 0
    subgraph_nodes: int = 0
    subgraph_edges: int = 0
    model_used: str = ""
    latency_ms: int = 0


class QueryResponse(BaseModel):
    """Final response returned to the user."""

    answer: str
    metadata: QueryMetadata = QueryMetadata()
    graph_context: str | None = None


class LLMRequest(BaseModel):
    """Internal request sent to the cloud LLM."""

    query: str
    context: str
    model: str | None = None


class LLMResponse(BaseModel):
    """Raw response from the cloud LLM (tokenized)."""

    raw_text: str
    model: str = ""
    usage: dict = {}
