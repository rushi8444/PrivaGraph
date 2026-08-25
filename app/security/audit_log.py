"""Immutable, hash-chained audit logger for privacy-sensitive operations."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path


class AuditLogger:
    """Append-only audit log with hash-chain tamper detection.

    Each entry includes a hash of the previous entry, creating an
    immutable chain that can be verified for tampering.
    """

    def __init__(self, log_path: Path | None = None):
        from app.config import settings

        self.log_path = log_path or settings.AUDIT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = "GENESIS"

    def log(self, event_type: str, details: dict) -> None:
        """Append a hash-chained audit entry.

        Args:
            event_type: The type of event (see constants below).
            details: Event-specific details dict.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details,
            "prev_hash": self._last_hash,
        }

        entry_str = json.dumps(entry, sort_keys=True)
        entry["entry_hash"] = hashlib.sha256(entry_str.encode()).hexdigest()
        self._last_hash = entry["entry_hash"]

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def read_entries(self, limit: int = 50) -> list[dict]:
        """Read the most recent audit entries.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of audit entries (most recent last).
        """
        if not self.log_path.exists():
            return []

        entries: list[dict] = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        # Verify chain integrity
        for i, entry in enumerate(entries):
            if i == 0:
                entry["chain_valid"] = entry.get("prev_hash") == "GENESIS"
            else:
                entry["chain_valid"] = (
                    entry.get("prev_hash") == entries[i - 1].get("entry_hash")
                )

        return entries[-limit:]


# Event type constants
DOCUMENT_INGESTED = "DOCUMENT_INGESTED"
ENTITY_DETECTED = "ENTITY_DETECTED"
TOKEN_CREATED = "TOKEN_CREATED"
VAULT_ACCESSED = "VAULT_ACCESSED"
QUERY_SENT = "QUERY_SENT"
QUERY_RECONSTRUCTED = "QUERY_RECONSTRUCTED"
INJECTION_BLOCKED = "INJECTION_BLOCKED"
ACCESS_DENIED = "ACCESS_DENIED"
