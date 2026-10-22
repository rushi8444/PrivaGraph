"""Query request and response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """User query submitted to the privacy-preserving pipeline."""

    query: str
    model: str | None = None
    max_traversal_depth: int = Field(default=3, ge=1, le=10)
    include_graph_context: bool = False
    conversation_id: str | None = None
    doc_ids: list[str] | None = None


class QueryMetadata(BaseModel):
    """Metadata about how a query was processed."""

    entities_reconstructed: int = 0
    subgraph_nodes: int = 0
    subgraph_edges: int = 0
    model_used: str = ""
    latency_ms: int = 0
    timings_ms: dict[str, int] = Field(default_factory=dict)


class Citation(BaseModel):
    """Source document citation for a retrieved fact."""

    doc_id: str
    title: str
    department: str = "General"
    classification: str = "INTERNAL"
    snippet: str | None = None
    predicate: str | None = None


class ZeroPIIProof(BaseModel):
    """Audit proof demonstrating that only anonymized tokens left the private perimeter."""

    tokenized_query: str
    anonymized_context: str
    raw_llm_response: str
    tokens_detected: list[str] = []
    entities_reconstructed: int = 0
    vault_storage_mode: str = "AES-256-GCM Encrypted (Local-Only)"
    egress_destination: str = "Cloud LLM (Zero Plaintext PII)"


class QueryResponse(BaseModel):
    """Final response returned to the user."""

    answer: str
    conversation_id: str | None = None
    metadata: QueryMetadata = QueryMetadata()
    graph_context: str | None = None
    citations: list[Citation] = []
    zero_pii_proof: ZeroPIIProof | None = None


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
