"""Token format encoder/decoder.

Handles the ⟦XX_TYPE_NNN⟧ token format used throughout the pipeline.
"""

from __future__ import annotations

import re

# Pattern to match tokens in text: ⟦XX_TYPE_NNN⟧
TOKEN_PATTERN = re.compile(r"\u27e6[A-Z0-9]{2}_[A-Z_]+_\d{3}\u27e7")


def find_tokens(text: str) -> list[str]:
    """Find all PrivaGraph tokens in a text string.

    Args:
        text: Text that may contain ⟦XX_TYPE_NNN⟧ tokens.

    Returns:
        List of token strings found in the text.
    """
    return TOKEN_PATTERN.findall(text)


def is_token(value: str) -> bool:
    """Check if a string is a valid PrivaGraph token."""
    return bool(TOKEN_PATTERN.fullmatch(value))
