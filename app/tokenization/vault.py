"""In-memory encrypted vault for MVP.

Stores token ↔ real value mappings with AES-256-GCM encryption.
This is the MVP implementation using an in-memory dictionary.
Production will migrate to PostgreSQL (see implementation plan Phase 2).
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.security.encryption import AESGCMCipher
from app.config import settings


class EncryptedVault:
    """Stores token ↔ real value mappings with AES-256-GCM encryption.

    MVP implementation uses an in-memory dictionary.
    Each stored value is individually encrypted with a unique nonce.
    """

    def __init__(self, cipher: AESGCMCipher | None = None):
        self.cipher = cipher or AESGCMCipher(settings.vault_key_bytes)
        # In-memory storage: token_id → {ciphertext, nonce, entity_type, doc_id, ...}
        self._store: dict[str, dict] = {}

    async def store(
        self,
        token: str,
        entity_type: str,
        original_value: str,
        hmac_digest: str,
        doc_id: str,
    ) -> None:
        """Encrypt and store a token mapping.

        Args:
            token: The opaque token (e.g. ⟦E7_PERSON_001⟧).
            entity_type: Entity type (e.g. PERSON, SALARY).
            original_value: The real PII value to encrypt.
            hmac_digest: HMAC digest for dedup lookups.
            doc_id: Source document ID.
        """
        if token in self._store:
            # Upgrade stored value if the new value is longer / more specific (e.g. full hyphenated name)
            try:
                old_val = self.cipher.decrypt(
                    self._store[token]["ciphertext"], self._store[token]["nonce"]
                ).decode("utf-8")
                if len(original_value) > len(old_val):
                    ciphertext, nonce = self.cipher.encrypt(original_value.encode("utf-8"))
                    self._store[token]["ciphertext"] = ciphertext
                    self._store[token]["nonce"] = nonce
            except Exception:
                pass
            return


        ciphertext, nonce = self.cipher.encrypt(original_value.encode("utf-8"))

        self._store[token] = {
            "ciphertext": ciphertext,
            "nonce": nonce,
            "entity_type": entity_type,
            "hmac_digest": hmac_digest,
            "doc_id": doc_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "accessed_at": None,
        }

    async def retrieve(self, token: str) -> str | None:
        """Decrypt and return the original value for a token.

        Args:
            token: The opaque token to look up.

        Returns:
            Decrypted original value, or None if token not found.
        """
        entry = self._store.get(token)
        if not entry:
            return None

        # Audit trail: record access time
        entry["accessed_at"] = datetime.now(timezone.utc).isoformat()

        return self.cipher.decrypt(entry["ciphertext"], entry["nonce"]).decode("utf-8")

    async def batch_retrieve(self, tokens: list[str]) -> dict[str, str]:
        """Efficiently decrypt multiple tokens.

        Args:
            tokens: List of opaque tokens to look up.

        Returns:
            Dictionary mapping tokens to their decrypted values.
        """
        result: dict[str, str] = {}
        now = datetime.now(timezone.utc).isoformat()

        for token in tokens:
            entry = self._store.get(token)
            if entry:
                result[token] = self.cipher.decrypt(
                    entry["ciphertext"], entry["nonce"]
                ).decode("utf-8")
                entry["accessed_at"] = now

        return result

    def count(self) -> int:
        """Return the number of stored tokens."""
        return len(self._store)
