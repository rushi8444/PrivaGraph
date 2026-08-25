"""Entity detection and tokenization models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DetectedEntity(BaseModel):
    """An entity detected by the PII/NER engine."""

    entity_type: str
    start: int
    end: int
    original_value: str
    confidence: float = Field(ge=0.0, le=1.0)


class TokenizedEntity(BaseModel):
    """A detected entity after deterministic tokenization."""

    token: str  # e.g. ⟦E7_PERSON_001⟧
    entity_type: str
    original_value: str
    hmac_digest: str
    confidence: float = Field(ge=0.0, le=1.0)
    start: int
    end: int
