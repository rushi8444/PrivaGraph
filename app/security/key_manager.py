"""Key management utilities."""

from __future__ import annotations

from app.security.encryption import AESGCMCipher


class KeyManager:
    """Manages master key derivation and rotation.

    MVP: Direct key loading from environment.
    Production: Integrate with HSM or cloud KMS.
    """

    @staticmethod
    def generate_master_key() -> str:
        """Generate a new random master key (hex-encoded).

        Returns:
            Hex string of a 256-bit key.
        """
        return AESGCMCipher.generate_key().hex()
