"""Custom domain-specific PII recognizers for Presidio.

Extends Presidio's built-in recognizers with enterprise-specific patterns
like salary amounts, project codes, and employee IDs.
"""

from __future__ import annotations

try:
    from presidio_analyzer import Pattern, PatternRecognizer
    HAS_PRESIDIO = True
except ImportError:
    HAS_PRESIDIO = False
    Pattern = None
    PatternRecognizer = None


def get_custom_recognizers():
    """Return domain-specific PII recognizers beyond Presidio defaults."""
    if not HAS_PRESIDIO:
        return []

    return [
        # Salary patterns: $185,000 or $2.3M or $185,000/year
        PatternRecognizer(
            supported_entity="SALARY",
            name="salary_recognizer",
            patterns=[
                Pattern(
                    name="dollar_amount",
                    regex=r"\$[\d,]+(?:\.\d+)?(?:[KMBkmb])?(?:/(?:year|yr|month|mo|hour|hr))?",
                    score=0.9,
                ),
            ],
            supported_language="en",
        ),
        # Internal project codes: PRJ-2026-XXXX
        PatternRecognizer(
            supported_entity="PROJECT_CODE",
            name="project_code_recognizer",
            patterns=[
                Pattern(
                    name="project_code",
                    regex=r"PRJ-\d{4}-[A-Z0-9]{4,}",
                    score=0.95,
                ),
            ],
            supported_language="en",
        ),
        # Internal employee IDs: EMP-XXXXX
        PatternRecognizer(
            supported_entity="EMPLOYEE_ID",
            name="employee_id_recognizer",
            patterns=[
                Pattern(
                    name="employee_id",
                    regex=r"EMP-\d{5,}",
                    score=0.95,
                ),
            ],
            supported_language="en",
        ),
    ]
