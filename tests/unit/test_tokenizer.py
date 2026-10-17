"""Unit tests for the deterministic tokenizer."""

import pytest

from app.models.entity import DetectedEntity
from app.tokenization.tokenizer import DeterministicTokenizer


class TestDeterministicTokenizer:
    """Tests for DeterministicTokenizer."""

    def setup_method(self):
        self.tokenizer = DeterministicTokenizer(secret_key=b"test-secret-key-1234567890abcdef")

    def test_tokenize_single_entity(self):
        """Tokenize a single entity produces a valid token."""
        entity = DetectedEntity(
            entity_type="PERSON",
            start=0,
            end=10,
            original_value="John Smith",
            confidence=0.95,
        )
        result = self.tokenizer.tokenize(entity)

        assert result.token.startswith("\u27e6")
        assert result.token.endswith("\u27e7")
        assert "PERSON" in result.token
        assert result.entity_type == "PERSON"
        assert result.original_value == "John Smith"

    def test_deterministic_same_entity(self):
        """Same entity always produces the same token."""
        entity = DetectedEntity(
            entity_type="PERSON",
            start=0,
            end=10,
            original_value="John Smith",
            confidence=0.95,
        )
        token1 = self.tokenizer.tokenize(entity)
        token2 = self.tokenizer.tokenize(entity)

        assert token1.token == token2.token
        assert token1.hmac_digest == token2.hmac_digest

    def test_different_entities_different_tokens(self):
        """Different entities produce different tokens."""
        entity1 = DetectedEntity(
            entity_type="PERSON", start=0, end=10,
            original_value="John Smith", confidence=0.95,
        )
        entity2 = DetectedEntity(
            entity_type="PERSON", start=0, end=12,
            original_value="Sarah Johnson", confidence=0.95,
        )
        token1 = self.tokenizer.tokenize(entity1)
        token2 = self.tokenizer.tokenize(entity2)

        assert token1.token != token2.token

    def test_tokenize_text(self):
        """Replace entities in text with tokens."""
        text = "John Smith earns $185,000/year."
        entities = [
            DetectedEntity(
                entity_type="PERSON", start=0, end=10,
                original_value="John Smith", confidence=0.95,
            ),
            DetectedEntity(
                entity_type="SALARY", start=17, end=29,
                original_value="$185,000/year", confidence=0.90,
            ),
        ]
        result_text, tok_entities = self.tokenizer.tokenize_text(text, entities)

        assert "John Smith" not in result_text
        assert "$185,000/year" not in result_text
        assert "\u27e6" in result_text
        assert len(tok_entities) == 2

    def test_different_secret_different_tokens(self):
        """Different secret keys produce different tokens for the same entity."""
        entity = DetectedEntity(
            entity_type="PERSON", start=0, end=10,
            original_value="John Smith", confidence=0.95,
        )
        tokenizer2 = DeterministicTokenizer(secret_key=b"different-secret-key-abcdefghij")
        token1 = self.tokenizer.tokenize(entity)
        token2 = tokenizer2.tokenize(entity)

        assert token1.token != token2.token

    def test_zero_collisions_high_entropy(self):
        """1,000 distinct entities must produce 1,000 completely unique tokens (zero collisions)."""
        tokens = set()
        for i in range(1000):
            ent = DetectedEntity(
                entity_type="PERSON", start=0, end=10,
                original_value=f"Employee Name {i}", confidence=0.95,
            )
            tok = self.tokenizer.tokenize(ent)
            tokens.add(tok.token)
        assert len(tokens) == 1000

    def test_compound_surname_vs_hyphenated_firstname(self):
        """Hyphenated compound surnames normalize to base name, but hyphenated first names are preserved."""
        # Compound surname with space -> maps to same token
        harold_full = DetectedEntity(entity_type="PERSON", start=0, end=20, original_value="Harold Mbeki-Sorensen", confidence=0.9)
        harold_base = DetectedEntity(entity_type="PERSON", start=0, end=12, original_value="Harold Mbeki", confidence=0.9)
        assert self.tokenizer.tokenize(harold_full).token == self.tokenizer.tokenize(harold_base).token

        # Hyphenated first name without space -> must NOT collapse into "Jean"
        jean_luc = DetectedEntity(entity_type="PERSON", start=0, end=8, original_value="Jean-Luc", confidence=0.9)
        jean_only = DetectedEntity(entity_type="PERSON", start=0, end=4, original_value="Jean", confidence=0.9)
        assert self.tokenizer.tokenize(jean_luc).token != self.tokenizer.tokenize(jean_only).token
