"""Token reconstructor.

Replaces opaque tokens in LLM responses with real decrypted values.
This happens LOCALLY — real data never leaves the corporate perimeter.
"""

from __future__ import annotations

from app.tokenization.token_codec import find_tokens
from app.tokenization.vault import EncryptedVault


class TokenReconstructor:
    """Replaces opaque tokens in LLM responses with real decrypted values."""

    def __init__(self, vault: EncryptedVault):
        self.vault = vault

    async def reconstruct(self, tokenized_response: str) -> tuple[str, int]:
        """Replace all tokens in the LLM response with real values.

        Args:
            tokenized_response: LLM response containing ⟦XX_TYPE_NNN⟧ tokens.

        Returns:
            Tuple of (reconstructed_text, entities_reconstructed_count).
        """
        tokens = find_tokens(tokenized_response)

        if not tokens:
            return tokenized_response, 0

        # Batch decrypt from vault
        token_map = await self.vault.batch_retrieve(tokens)

        # Replace tokens with real values
        result = tokenized_response
        for token, real_value in token_map.items():
            result = result.replace(token, real_value)

        return result, len(token_map)
