"""Prompt injection sanitizer.

Detects and blocks prompt injection attacks in retrieved context,
implementing OWASP LLM Top 10 defenses against instruction overrides,
data exfiltration attempts, role hijacking, and vault probing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SanitizationResult:
    """Result of scanning context for prompt injection attacks."""

    is_safe: bool
    sanitized_text: str
    violations: list[str] = field(default_factory=list)


class PromptSanitizer:
    """Detects and blocks prompt injection attacks in retrieved context."""

    # Patterns that indicate prompt injection attempts
    INJECTION_PATTERNS: list[tuple[str, str]] = [
        # Instruction overrides
        (
            r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
            "Instruction override attempt",
        ),
        (r"you\s+are\s+now\s+(?:a|an)\s+", "Role hijacking attempt"),
        (r"system\s*:\s*", "System prompt injection"),
        (r"<\|(?:im_start|system|assistant)\|>", "Chat template injection"),
        # Data exfiltration
        (
            r"(?:output|print|show|reveal|display)\s+(?:the\s+)?(?:system|original|real|hidden)\s+",
            "Data exfiltration attempt",
        ),
        (r"(?:fetch|curl|wget|http|https)://", "URL injection attempt"),
        # Vault probing
        (
            r"\b(?:vault\s+(?:contents?|passwords?|keys?|data|secrets?)|api[_\s\-]?keys?|master[_\s\-]?keys?|private[_\s\-]?keys?|token[_\s\-]?vault|encryption[_\s\-]?keys?)\b|"
            r"\b(?:show|reveal|display|dump|extract|leak|expose|steal)\b(?:\s+\w+){0,4}\s+\b(?:vault|passwords?|credentials?|api[_\s\-]?keys?|master[_\s\-]?keys?|private[_\s\-]?keys?|token[_\s\-]?vault)\b",
            "Vault probing attempt",
        ),
        (
            r"\b(?:decrypt\s+(?:all|the|tokens?|data)|decryption\s+key|master[_\s\-]?key|private[_\s\-]?key)\b",
            "Decryption probing attempt",
        ),
    ]

    def __init__(self):
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), desc)
            for pattern, desc in self.INJECTION_PATTERNS
        ]

    def sanitize(self, context_text: str) -> SanitizationResult:
        """Scan context for injection patterns. Block if found.

        Args:
            context_text: The retrieved context text to scan.

        Returns:
            SanitizationResult indicating safety and any violations.
        """
        violations: list[str] = []

        for pattern, description in self._compiled_patterns:
            if pattern.search(context_text):
                violations.append(description)

        if violations:
            return SanitizationResult(
                is_safe=False,
                sanitized_text="",
                violations=violations,
            )

        return SanitizationResult(
            is_safe=True,
            sanitized_text=context_text,
            violations=[],
        )
