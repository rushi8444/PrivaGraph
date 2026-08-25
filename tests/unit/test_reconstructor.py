"""Unit tests for the token reconstructor."""

import pytest

from app.tokenization.vault import EncryptedVault
from app.proxy.reconstructor import TokenReconstructor
from app.security.encryption import AESGCMCipher


@pytest.fixture
def vault():
    """Create a vault with test data."""
    key = AESGCMCipher.generate_key()
    cipher = AESGCMCipher(key)
    return EncryptedVault(cipher=cipher)


@pytest.fixture
def reconstructor(vault):
    """Create a reconstructor with the test vault."""
    return TokenReconstructor(vault)


class TestTokenReconstructor:
    """Tests for TokenReconstructor."""

    @pytest.mark.asyncio
    async def test_reconstruct_single_token(self, vault, reconstructor):
        """Reconstruct a single token to its real value."""
        await vault.store(
            token="\u27e6E7_PERSON_001\u27e7",
            entity_type="PERSON",
            original_value="John Smith",
            hmac_digest="abc123",
            doc_id="TEST-001",
        )

        text = "The answer is \u27e6E7_PERSON_001\u27e7 manages the team."
        result, count = await reconstructor.reconstruct(text)

        assert "John Smith" in result
        assert "\u27e6E7_PERSON_001\u27e7" not in result
        assert count == 1

    @pytest.mark.asyncio
    async def test_reconstruct_multiple_tokens(self, vault, reconstructor):
        """Reconstruct multiple tokens in one response."""
        await vault.store(
            token="\u27e6E7_PERSON_001\u27e7",
            entity_type="PERSON",
            original_value="John Smith",
            hmac_digest="abc123",
            doc_id="TEST-001",
        )
        await vault.store(
            token="\u27e6B1_SALARY_001\u27e7",
            entity_type="SALARY",
            original_value="$185,000/year",
            hmac_digest="def456",
            doc_id="TEST-001",
        )

        text = "\u27e6E7_PERSON_001\u27e7 earns \u27e6B1_SALARY_001\u27e7."
        result, count = await reconstructor.reconstruct(text)

        assert "John Smith" in result
        assert "$185,000/year" in result
        assert count == 2

    @pytest.mark.asyncio
    async def test_no_tokens_returns_unchanged(self, reconstructor):
        """Text without tokens is returned unchanged."""
        text = "No tokens in this text."
        result, count = await reconstructor.reconstruct(text)

        assert result == text
        assert count == 0

    @pytest.mark.asyncio
    async def test_unknown_token_left_in_place(self, reconstructor):
        """Tokens not in the vault remain in the text."""
        text = "\u27e6ZZ_UNKNOWN_999\u27e7 is not in the vault."
        result, count = await reconstructor.reconstruct(text)

        assert "\u27e6ZZ_UNKNOWN_999\u27e7" in result
        assert count == 0
