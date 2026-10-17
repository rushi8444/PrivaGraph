"""In-memory encrypted vault for MVP.

Stores token ↔ real value mappings with AES-256-GCM encryption.
This is the MVP implementation using an in-memory dictionary.
Production will migrate to PostgreSQL (see implementation plan Phase 2).
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import sqlite3
from pathlib import Path

from app.security.encryption import AESGCMCipher
from app.config import settings


class EncryptedVault:
    """Stores token ↔ real value mappings with AES-256-GCM encryption.

    Uses an in-memory dictionary cache with optional SQLite persistent storage.
    Each stored value is individually encrypted with a unique nonce.
    """

    def __init__(self, cipher: AESGCMCipher | None = None, db_path: Path | str | None = None):
        self.cipher = cipher or AESGCMCipher(settings.vault_key_bytes)
        self.db_path = Path(db_path) if db_path else None
        # In-memory storage: token_id → {ciphertext, nonce, entity_type, doc_id, ...}
        self._store: dict[str, dict] = {}

        if self.db_path:
            self._init_db()
            self._load_from_db()

    @contextlib.contextmanager
    def _get_connection(self):
        """Yield a managed SQLite connection that commits and closes cleanly."""
        if not self.db_path:
            raise RuntimeError("Database path is not configured.")
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize SQLite table for persistent encrypted storage."""
        if not self.db_path:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vault_entries (
                    token TEXT PRIMARY KEY,
                    ciphertext BLOB NOT NULL,
                    nonce BLOB NOT NULL,
                    entity_type TEXT NOT NULL,
                    hmac_digest TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    accessed_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_id ON vault_entries(doc_id)")
            conn.commit()

    def _load_from_db(self) -> None:
        """Load encrypted entries from SQLite into in-memory cache."""
        if not self.db_path or not self.db_path.exists():
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT token, ciphertext, nonce, entity_type, hmac_digest, doc_id, created_at, accessed_at FROM vault_entries"
            )
            for row in cursor.fetchall():
                token, ciphertext, nonce, entity_type, hmac_digest, doc_id, created_at, accessed_at = row
                self._store[token] = {
                    "ciphertext": ciphertext,
                    "nonce": nonce,
                    "entity_type": entity_type,
                    "hmac_digest": hmac_digest,
                    "doc_id": doc_id,
                    "created_at": created_at,
                    "accessed_at": accessed_at,
                }

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
        now = datetime.now(timezone.utc).isoformat()
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
                    if self.db_path:
                        with self._get_connection() as conn:
                            conn.execute(
                                "UPDATE vault_entries SET ciphertext = ?, nonce = ? WHERE token = ?",
                                (ciphertext, nonce, token),
                            )
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
            "created_at": now,
            "accessed_at": None,
        }

        if self.db_path:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO vault_entries
                    (token, ciphertext, nonce, entity_type, hmac_digest, doc_id, created_at, accessed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (token, ciphertext, nonce, entity_type, hmac_digest, doc_id, now, None),
                )

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

    def delete_by_doc_id(self, doc_id: str) -> int:
        """Purge all stored tokens associated with a document ID."""
        to_delete = [
            token
            for token, entry in self._store.items()
            if entry.get("doc_id") == doc_id
        ]
        for token in to_delete:
            del self._store[token]

        if self.db_path and self.db_path.exists():
            with self._get_connection() as conn:
                conn.execute("DELETE FROM vault_entries WHERE doc_id = ?", (doc_id,))

        return len(to_delete)

    def clear(self) -> None:
        """Clear all stored entries from memory and persistent database."""
        self._store.clear()
        if self.db_path and self.db_path.exists():
            with self._get_connection() as conn:
                conn.execute("DELETE FROM vault_entries")

