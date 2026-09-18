"""Unified cloud LLM gateway.

Sends ONLY anonymized/tokenized context to cloud LLM APIs.
Supports OpenAI, Anthropic, and Google providers.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.models.query import LLMRequest, LLMResponse


SYSTEM_PROMPT = (
    "You are a precise data answer synthesizer. Your job is to answer the user's query using ONLY the provided graph context.\n\n"
    "CRITICAL CONSTRAINTS:\n"
    "1. STRICT FACT MATCHING: Answer ONLY what the user explicitly asks for.\n"
    "   - If the user asks for a Social Security Number, provide ONLY the Social Security Number.\n"
    "   - DO NOT list adjacent entity properties (such as salary, address, manager, or title) unless the user explicitly asks for a full profile.\n"
    "2. CONCISE FORMATTING: State the requested answer directly in 1 sentence.\n"
    "3. ANONYMIZED TOKENS: The context contains anonymized entity tokens in the format ⟦XX_TYPE_NNN⟧. "
    "Always preserve their exact brackets and casing (e.g. ⟦XX_TYPE_NNN⟧) so they can be securely resolved locally.\n\n"
    "[Bad Example]\n"
    "Query: \"What is John's SSN?\"\n"
    "Context: {Name: John, SSN: 123, Salary: $50k, Address: Main St}\n"
    "Response: \"John earns $50k, lives on Main St, and his SSN is 123.\" (INCORRECT - Over-disclosed)\n\n"
    "[Good Example]\n"
    "Query: \"What is John's SSN?\"\n"
    "Context: {Name: John, SSN: 123, Salary: $50k, Address: Main St}\n"
    "Response: \"John's Social Security Number is 123.\" (CORRECT)"
)




class LLMGateway:
    """Unified gateway to cloud LLM APIs."""

    def __init__(self, provider: str | None = None, api_key: str | None = None):
        self.provider = provider or settings.LLM_PROVIDER
        self.api_key = api_key or settings.LLM_API_KEY
        self.client = httpx.AsyncClient(timeout=60.0)

    async def query(self, request: LLMRequest) -> LLMResponse:
        """Send anonymized context + query to cloud LLM.

        Args:
            request: LLM request with tokenized context and user query.

        Returns:
            LLMResponse with the raw (tokenized) answer.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        model = request.model or settings.DEFAULT_MODEL

        if self.provider == "openai":
            return await self._query_openai(request, model)
        elif self.provider == "anthropic":
            return await self._query_anthropic(request, model)
        elif self.provider in ("google", "gemini"):
            return await self._query_google(request, model)
        else:
            # Fallback: return a placeholder for providers not yet implemented
            return LLMResponse(
                raw_text=f"[LLM provider '{self.provider}' not yet implemented. Context received: {len(request.context)} chars]",
                model=model,
            )

    async def _query_google(self, request: LLMRequest, model: str) -> LLMResponse:
        """Query Google Gemini API."""
        # Normalize model name if user provided e.g. "gemini-2.5-flash" vs "models/gemini-2.5-flash"
        model_name = model if not model.startswith("models/") else model[len("models/"):]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"Context:\n{request.context}\n\nQuestion: {request.query}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
            },
        }

        import asyncio
        import logging
        logger = logging.getLogger("uvicorn.error")

        data = {}
        for attempt in range(3):
            response = await self.client.post(url, json=payload)
            if response.status_code == 429 and attempt < 2:
                await asyncio.sleep(2.0 * (attempt + 1))
                continue
            response.raise_for_status()
            data = response.json()
            break

        raw_text = ""
        candidates = data.get("candidates", [])
        if candidates:
            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])
            if parts:
                raw_text = parts[0].get("text", "")
            else:
                finish_reason = candidate.get("finishReason", "UNKNOWN")
                logger.warning(
                    f"Gemini API returned candidate with no text parts. Finish reason: {finish_reason}. Candidate: {candidate}"
                )
                raise ValueError(f"Gemini blocked or returned empty content (finishReason: {finish_reason})")
        else:
            prompt_feedback = data.get("promptFeedback", {})
            logger.warning(f"Gemini API returned no candidates. Prompt feedback: {prompt_feedback}")
            raise ValueError(f"Gemini returned no candidates (feedback: {prompt_feedback})")

        if not raw_text.strip():
            logger.warning("Gemini API returned whitespace-only text.")
            raise ValueError("Gemini returned empty text.")

        return LLMResponse(
            raw_text=raw_text,
            model=model,
            usage=data.get("usageMetadata", {}),
        )

    async def _query_openai(self, request: LLMRequest, model: str) -> LLMResponse:
        """Query OpenAI-compatible API."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Context:\n{request.context}\n\nQuestion: {request.query}",
                },
            ],
            "temperature": 0.1,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = await self.client.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            raw_text=data["choices"][0]["message"]["content"],
            model=data.get("model", model),
            usage=data.get("usage", {}),
        )

    async def _query_anthropic(self, request: LLMRequest, model: str) -> LLMResponse:
        """Query Anthropic Claude API."""
        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": f"Context:\n{request.context}\n\nQuestion: {request.query}",
                },
            ],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        response = await self.client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            raw_text=data["content"][0]["text"],
            model=data.get("model", model),
            usage=data.get("usage", {}),
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
