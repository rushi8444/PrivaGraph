"""Integration tests for FastAPI endpoints."""

from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_health_check():
    """Verify health endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_document_ingestion_and_query_flow():
    """Test full pipeline: upload document -> check graph -> query -> check audit log."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Ingest HR doc
        hr_file_path = FIXTURES_DIR / "sample_hr_doc.md"
        with open(hr_file_path, "rb") as f:
            files = {"file": ("sample_hr_doc.md", f, "text/markdown")}
            response = await ac.post("/api/v1/documents/ingest", files=files)
        
        assert response.status_code == 200
        ingest_data = response.json()
        assert ingest_data["status"] == "ingested"
        assert ingest_data["doc_id"] == "HR-2026-00142"
        assert ingest_data["entities_detected"] > 0

        # 2. List documents
        doc_list_res = await ac.get("/api/v1/documents")
        assert doc_list_res.status_code == 200
        docs = doc_list_res.json()["documents"]
        assert any(d["id"] == "HR-2026-00142" for d in docs)

        # 3. Check graph nodes
        graph_res = await ac.get("/api/v1/graph/nodes")
        assert graph_res.status_code == 200
        graph_data = graph_res.json()
        assert len(graph_data["nodes"]) > 0

        # 4. Check graph stats
        stats_res = await ac.get("/api/v1/graph/stats")
        assert stats_res.status_code == 200
        assert stats_res.json()["total_nodes"] > 0

        # 5. Query the system
        query_payload = {
            "query": "Who manages the team budget?",
            "include_graph_context": True,
        }
        query_res = await ac.post("/api/v1/query", json=query_payload)
        assert query_res.status_code == 200
        query_data = query_res.json()
        assert "answer" in query_data
        assert query_data["metadata"]["subgraph_nodes"] > 0

        # 6. Check audit log
        audit_res = await ac.get("/api/v1/admin/audit-log")
        assert audit_res.status_code == 200
        entries = audit_res.json()["entries"]
        assert len(entries) > 0
        assert any(e["event_type"] == "DOCUMENT_INGESTED" for e in entries)
