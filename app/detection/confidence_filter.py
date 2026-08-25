"""Confidence filter — post-processing for detected entities."""

from __future__ import annotations

from app.models.entity import DetectedEntity


def filter_by_confidence(
    entities: list[DetectedEntity],
    min_confidence: float = 0.85,
) -> list[DetectedEntity]:
    """Filter entities below the confidence threshold."""
    return [e for e in entities if e.confidence >= min_confidence]
