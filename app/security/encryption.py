"""AES-256-GCM authenticated encryption for vault values."""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AESGCMCipher:
    """AES-256-GCM authenticated encryption.

    Provides encrypt/decrypt with random nonces and authentication tags.
    Each encryption produces a unique ciphertext even for identical plaintexts.
    """

    NONCE_SIZE = 12  # 96 bits — recommended for GCM
    KEY_SIZE = 32  # 256 bits

    def __init__(self, key: bytes):
        if len(key) != self.KEY_SIZE:
            raise ValueError(f"Key must be {self.KEY_SIZE} bytes (got {len(key)})")
        self._aesgcm = AESGCM(key)

    def encrypt(self, plaintext: bytes) -> tuple[bytes, bytes]:
        """Encrypt with a random nonce.

        Returns:
            Tuple of (ciphertext, nonce).
        """
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
        return ciphertext, nonce

    def decrypt(self, ciphertext: bytes, nonce: bytes) -> bytes:
        """Decrypt and verify authentication tag.

        Raises:
            cryptography.exceptions.InvalidTag: If ciphertext was tampered with.
        """
        return self._aesgcm.decrypt(nonce, ciphertext, None)

    @classmethod
    def generate_key(cls) -> bytes:
        """Generate a cryptographically secure random 256-bit key."""
        return os.urandom(cls.KEY_SIZE)
