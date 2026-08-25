"""OWASP trust boundary enforcement."""

from __future__ import annotations

from enum import Enum


class TrustZone(Enum):
    """OWASP-aligned trust zones."""

    LOCAL_TRUSTED = "local_trusted"
    LOCAL_UNTRUSTED = "local_untrusted"
    EXTERNAL_UNTRUSTED = "external"


def validate_flow(source: TrustZone, destination: TrustZone, data_type: str) -> bool:
    """Validate that a data flow between zones is permitted.

    Args:
        source: The originating trust zone.
        destination: The target trust zone.
        data_type: Type of data being transferred.

    Returns:
        True if the flow is permitted, False otherwise.
    """
    if data_type == "raw_pii":
        return destination == TrustZone.LOCAL_TRUSTED

    if data_type == "tokenized":
        return True  # Tokenized data can flow anywhere

    if data_type == "vault_lookup":
        return source == TrustZone.LOCAL_TRUSTED

    return True
