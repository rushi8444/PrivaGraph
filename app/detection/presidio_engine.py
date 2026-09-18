"""Microsoft Presidio-based PII detection engine with graceful regex fallback.

Wraps the Presidio AnalyzerEngine to detect personally identifiable information
and other sensitive entities in text, with support for custom domain-specific
recognizers and configurable confidence thresholds.
"""

from __future__ import annotations

import re
from app.detection.custom_recognizers import get_custom_recognizers
from app.models.entity import DetectedEntity

try:
    from presidio_analyzer import AnalyzerEngine, RecognizerResult
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    HAS_PRESIDIO = True
except ImportError:
    HAS_PRESIDIO = False
    AnalyzerEngine = None
    RecognizerResult = None
    NlpEngineProvider = None


class FallbackPIIDetector:
    """Built-in regex & rule-based PII detector when Presidio is not installed."""

    PATTERNS: list[tuple[str, str, float]] = [
        # (regex, entity_type, score)
        (r"\b\d{3}-\d{2}-\d{4}\b", "US_SSN", 0.95),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL_ADDRESS", 0.95),
        (r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "PHONE_NUMBER", 0.88),
        (r"\$[\d,]+(?:\.\d+)?(?:[KMBkmb])?(?:/(?:year|yr|month|mo|hour|hr))?", "SALARY", 0.92),
        (r"PRJ-\d{4}-[A-Z0-9]{4,}", "PROJECT_CODE", 0.95),
        (r"EMP-\d{5,}", "EMPLOYEE_ID", 0.95),
        (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b", "CREDIT_CARD", 0.95),
        # Capitalized two-word names with optional hyphenated surname (heuristic for PERSON)
        (r"\b[A-Z][a-z]+ [A-Z][a-z]+(?:-[A-Za-z]+)?\b", "PERSON", 0.86),
        # US Street Address pattern: e.g. 2 Overlook Pointe, Sewickley, PA 15143
        (r"\b\d+\s+[A-Za-z0-9\s,.-]+?(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Circle|Cir|Pointe|Place|Pl|Terrace|Ter|Row)\b(?:,\s*[A-Za-z\s]+)?(?:,\s*[A-Z]{2}\s+\d{5})?", "LOCATION", 0.90),
    ]

    def detect(
        self,
        text: str,
        entity_categories: list[str] | None = None,
        min_confidence: float = 0.85,
    ) -> list[DetectedEntity]:
        detected = []
        for pattern, entity_type, score in self.PATTERNS:
            if entity_categories and entity_type not in entity_categories:
                # Also check aliases like SSN -> US_SSN
                if not any(cat in entity_type or entity_type in cat for cat in entity_categories):
                    continue
            if score < min_confidence:
                continue

            NON_PERSON_WORDS = {
                "senior engineer", "junior engineer", "software engineer", "staff engineer",
                "vice president", "human resources", "compensation review", "project manager",
                "product manager", "team lead", "executive officer", "finance team", "engineering team",
                "chief executive", "chief technology", "chief financial", "security review",
                "social security", "security number", "security officer", "information security",
            }

            for match in re.finditer(pattern, text):
                val = match.group(0)
                if entity_type == "PERSON" and (val.lower() in NON_PERSON_WORDS or "social security" in val.lower()):
                    continue

                detected.append(
                    DetectedEntity(
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        original_value=val,
                        confidence=score,
                    )
                )

        # Sort by start pos and deduplicate
        detected = sorted(detected, key=lambda e: (e.start, -e.confidence))
        filtered = []
        for d in detected:
            if not any(d.start < ex.end and ex.start < d.end for ex in filtered):
                filtered.append(d)
        return sorted(filtered, key=lambda e: e.start)


class PresidioDetectionEngine:
    """Wraps Microsoft Presidio for PII entity detection, falling back to rule-based engine if unavailable."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.use_presidio = False
        if HAS_PRESIDIO:
            try:
                provider = NlpEngineProvider(
                    nlp_configuration={
                        "nlp_engine_name": "spacy",
                        "models": [{"lang_code": "en", "model_name": model_name}],
                    }
                )
                self.analyzer = AnalyzerEngine(
                    nlp_engine=provider.create_engine(),
                    supported_languages=["en"],
                )
                for recognizer in get_custom_recognizers():
                    self.analyzer.registry.add_recognizer(recognizer)
                self.use_presidio = True
            except Exception:
                self.use_presidio = False

        if not self.use_presidio:
            self.fallback_engine = FallbackPIIDetector()

    def detect(
        self,
        text: str,
        entity_categories: list[str] | None = None,
        min_confidence: float = 0.85,
        language: str = "en",
    ) -> list[DetectedEntity]:
        """Detect PII entities in text, filtered by OKF-declared categories."""
        if not self.use_presidio:
            return self.fallback_engine.detect(
                text=text,
                entity_categories=entity_categories,
                min_confidence=min_confidence,
            )

        results: list[RecognizerResult] = self.analyzer.analyze(
            text=text,
            entities=entity_categories,
            language=language,
            score_threshold=min_confidence,
        )

        # Expand PERSON entities if immediately followed by a hyphenated surname
        expanded_results = []
        for r in results:
            if r.entity_type == "PERSON":
                m = re.match(r"^-[A-Za-z]+(?:\b|$)", text[r.end :])
                if m:
                    r.end = r.end + len(m.group(0))
            expanded_results.append(r)

        results = self._resolve_overlaps(expanded_results)

        return [
            DetectedEntity(
                entity_type=r.entity_type,
                start=r.start,
                end=r.end,
                original_value=text[r.start : r.end],
                confidence=r.score,
            )
            for r in results
        ]

    def _resolve_overlaps(
        self, results: list[RecognizerResult]
    ) -> list[RecognizerResult]:
        """When two detections overlap, keep the one with higher confidence."""
        if not results:
            return []

        sorted_results = sorted(results, key=lambda r: (-r.score, r.start))
        filtered: list[RecognizerResult] = []

        for candidate in sorted_results:
            overlaps = any(
                self._spans_overlap(candidate, existing) for existing in filtered
            )
            if not overlaps:
                filtered.append(candidate)

        return sorted(filtered, key=lambda r: r.start)

    @staticmethod
    def _spans_overlap(a: RecognizerResult, b: RecognizerResult) -> bool:
        """Check if two detection spans overlap."""
        return a.start < b.end and b.start < a.end
