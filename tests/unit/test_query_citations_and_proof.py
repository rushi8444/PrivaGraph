"""Unit tests for query citations and Zero-PII proof models and endpoints."""

from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.query import Citation, ZeroPIIProof, QueryResponse
from app.tokenization.token_codec import extract_tokens

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_query_returns_citations_and_zero_pii_proof():
    """Verify that submitting a query returns structured citations and cryptographic proof."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ingest a sample document first to populate graph
        hr_file_path = FIXTURES_DIR / "sample_hr_doc.md"
        with open(hr_file_path, "rb") as f:
            files = {"file": ("sample_hr_doc.md", f, "text/markdown")}
            ingest_res = await ac.post("/api/v1/documents/ingest", files=files)
        assert ingest_res.status_code == 200

        # Query for employee information
        query_payload = {"query": "What department is Sarah Chen in?"}
        res = await ac.post("/api/v1/query", json=query_payload)
        assert res.status_code == 200
        data = res.json()

        # Check citations
        assert "citations" in data
        assert isinstance(data["citations"], list)
        if data["citations"]:
            first_cit = data["citations"][0]
            assert "doc_id" in first_cit
            assert "title" in first_cit
            assert "department" in first_cit
            assert "classification" in first_cit
            assert "snippet" in first_cit
            assert "predicate" in first_cit
            # Verify no token remains in reconstructed snippet if it was reconstructed
            assert "⟦" not in (first_cit["snippet"] or "")

        # Check Zero-PII proof
        assert "zero_pii_proof" in data
        proof = data["zero_pii_proof"]
        assert proof is not None
        assert "tokenized_query" in proof
        assert "anonymized_context" in proof
        assert "raw_llm_response" in proof
        assert "tokens_detected" in proof
        assert "vault_storage_mode" in proof
        assert "egress_destination" in proof
        assert "AES-256-GCM" in proof["vault_storage_mode"]

        # Ensure that plaintext PII does not leak into tokenized_query or anonymized_context
        # E.g., Sarah Chen should be tokenized in tokenized_query
        assert "Sarah Chen" not in proof["tokenized_query"]
