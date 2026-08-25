"""Deterministic HMAC-based entity tokenizer.

Generates opaque, deterministic tokens for detected PII entities.
The same (entity_type, original_value) always produces the same token,
enabling cross-document entity linking in the knowledge graph.

Token format: ⟦E7_PERSON_001⟧
  - E7      = first 2 chars of HMAC digest (collision namespace)
  - TYPE    = entity type
  - NNN     = sequential counter per type
"""

from __future__ import annotations

import hmac
import hashlib
from collections import defaultdict

from app.models.entity import DetectedEntity, TokenizedEntity
from app.config import settings


class DeterministicTokenizer:
    """Generates deterministic, opaque tokens for detected entities."""

    def __init__(self, secret_key: bytes | None = None):
        self.secret_key = secret_key or settings.TOKENIZER_SECRET_KEY.encode()
        # Maps (entity_type, hmac_digest) → token_id for deterministic reuse
        self._token_map: dict[str, str] = {}
        self._type_counters: dict[str, int] = defaultdict(int)

    def tokenize(self, entity: DetectedEntity) -> TokenizedEntity:
        """Generate a deterministic opaque token for an entity.

        Args:
            entity: A detected entity to tokenize.

        Returns:
            TokenizedEntity with the opaque token and HMAC digest.
        """
        # Normalize entity type and value for robust cross-document / cross-query matching
        norm_type = entity.entity_type.upper().strip()
        norm_val = entity.original_value.strip().lower()

        digest = hmac.new(
            self.secret_key,
            f"{norm_type}:{norm_val}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        lookup_key = f"{norm_type}:{digest}"

        if lookup_key not in self._token_map:
            prefix = digest[:2].upper()
            suffix_num = int(digest[2:6], 16) % 1000
            token = f"\u27e6{prefix}_{norm_type}_{suffix_num:03d}\u27e7"
            self._token_map[lookup_key] = token

        return TokenizedEntity(
            token=self._token_map[lookup_key],
            entity_type=entity.entity_type,
            original_value=entity.original_value,
            hmac_digest=digest,
            confidence=entity.confidence,
            start=entity.start,
            end=entity.end,
        )

    def tokenize_text(
        self, text: str, entities: list[DetectedEntity]
    ) -> tuple[str, list[TokenizedEntity]]:
        """Replace all detected entities in text with their opaque tokens.

        Args:
            text: Original text containing PII.
            entities: List of detected entities to replace.

        Returns:
            Tuple of (tokenized_text, list_of_tokenized_entities).
        """
        # Sort by position (reverse) to replace from end to start
        # This preserves character offsets during replacement
        sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)
        tokenized_entities: list[TokenizedEntity] = []
        result = text

        for entity in sorted_entities:
            tok_entity = self.tokenize(entity)
            tokenized_entities.append(tok_entity)
            result = result[: entity.start] + tok_entity.token + result[entity.end :]

        return result, list(reversed(tokenized_entities))

    def get_token_map(self) -> dict[str, str]:
        """Return the current token → lookup_key mapping (for debugging)."""
        return dict(self._token_map)
