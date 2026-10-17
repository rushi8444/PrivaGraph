"""Merge schema-derived typed hints (e.g. from CSV/XLSX columns) with NER output.

Hints win on any overlap: a hinted span with an entity type is emitted as a
confidence-1.0 entity; a hinted span without a type is a plain attribute that
must not be tokenized, so overlapping NER detections are dropped.
"""

from __future__ import annotations

from app.models.document import TypedSpan
from app.models.entity import DetectedEntity


def merge_hints(
    sentence: str,
    detected: list[DetectedEntity],
    hints: list[TypedSpan] | None,
    allowed_types: list[str] | None = None,
) -> list[DetectedEntity]:
    if not hints:
        return detected

    typed: list[DetectedEntity] = []
    for h in hints:
        if h.entity_type and (not allowed_types or h.entity_type in allowed_types):
            typed.append(
                DetectedEntity(
                    entity_type=h.entity_type,
                    start=h.start,
                    end=h.end,
                    original_value=sentence[h.start : h.end],
                    confidence=1.0,
                )
            )

    def overlaps_hint(e: DetectedEntity) -> bool:
        return any(e.start < h.end and h.start < e.end for h in hints)

    kept = [e for e in detected if not overlaps_hint(e)]
    return sorted(kept + typed, key=lambda e: e.start)
