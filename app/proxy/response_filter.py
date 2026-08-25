"""Response output filter — scans LLM responses for PII leaks."""

from __future__ import annotations

import re


class ResponseFilter:
    """Scans LLM responses for accidental PII leaks from training data.

    Acts as a safety net: even though the LLM only receives tokenized context,
    it could hallucinate PII from its training data. This filter catches
    common patterns and flags them.
    """

    PII_PATTERNS: list[tuple[str, str]] = [
        (r"\b\d{3}-\d{2}-\d{4}\b", "SSN pattern detected"),
        (r"\b\d{16}\b", "Credit card number pattern detected"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email pattern detected"),
    ]

    def __init__(self):
        self._compiled = [
            (re.compile(p), desc) for p, desc in self.PII_PATTERNS
        ]

    def scan(self, response_text: str) -> list[str]:
        """Scan response for PII patterns.

        Args:
            response_text: The reconstructed response to scan.

        Returns:
            List of warning messages for detected patterns.
        """
        warnings: list[str] = []
        for pattern, desc in self._compiled:
            if pattern.search(response_text):
                warnings.append(desc)
        return warnings
