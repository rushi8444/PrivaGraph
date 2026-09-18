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


@pytest.mark.asyncio
async def test_pdf_document_ingestion_flow():
    """Test PDF upload, auto-conversion to OKF, PII detection, and graph inclusion."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        pdf_path = FIXTURES_DIR / "sample_employee_record.pdf"
        with open(pdf_path, "rb") as f:
            files = {"file": ("sample_employee_record.pdf", f, "application/pdf")}
            data = {"department": "Cloud Engineering", "classification": "CONFIDENTIAL"}
            response = await ac.post("/api/v1/documents/ingest", files=files, data=data)

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "ingested"
        assert result["doc_id"].startswith("PDF-")
        assert result["entities_detected"] > 0
        assert result["tokens_stored"] > 0

        # Verify it appears in document list with overridden department & classification
        doc_list_res = await ac.get("/api/v1/documents")
        assert doc_list_res.status_code == 200
        docs = doc_list_res.json()["documents"]
        matching = next((d for d in docs if d["id"] == result["doc_id"]), None)
        assert matching is not None
        assert matching["department"] == "Cloud Engineering"
        assert matching["classification"] == "CONFIDENTIAL"


@pytest.mark.asyncio
async def test_unsupported_file_format_rejected():
    """Verify non-markdown and non-pdf files are rejected with 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = {"file": ("spreadsheet.xlsx", b"dummy content", "application/octet-stream")}
        response = await ac.post("/api/v1/documents/ingest", files=files)
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_table_pdf_ingestion_and_uncontaminated_queries():
    """Regression test: PDF table ingestion guarantees uncontaminated single-fact lookups."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Ingest sample payroll table PDF
        table_pdf_path = FIXTURES_DIR / "sample_payroll_table.pdf"
        with open(table_pdf_path, "rb") as f:
            files = {"file": ("sample_payroll_table.pdf", f, "application/pdf")}
            ingest_res = await ac.post("/api/v1/documents/ingest", files=files)

        assert ingest_res.status_code == 200
        assert ingest_res.json()["status"] == "ingested"

        # 2. Query Priya's SSN: must return her SSN and ZERO cross-contamination
        q1_res = await ac.post("/api/v1/query", json={"query": "What is Priya Nandakumar's SSN?"})
        assert q1_res.status_code == 200
        a1 = q1_res.json()["answer"]
        assert a1 != ""
        assert "912-04-7731" in a1
        assert "927-18-3364" not in a1
        assert "905-62-1187" not in a1
        assert "$118,000" not in a1

        # 3. Query Marcus's salary: must return $196,000 and ZERO other salaries
        q2_res = await ac.post("/api/v1/query", json={"query": "What is Marcus Feldstein's salary?"})
        assert q2_res.status_code == 200
        a2 = q2_res.json()["answer"]
        assert "$196,000" in a2
        assert "$142,500" not in a2
        assert "$118,000" not in a2

        # 4. Query Marcus's reason: must return Promotion
        q3_res = await ac.post("/api/v1/query", json={"query": "What is the reason for Marcus Feldstein's compensation?"})
        assert q3_res.status_code == 200
        a3 = q3_res.json()["answer"]
        assert "Promotion" in a3

        # 5. Query absent fact: must report not found honestly
        q4_res = await ac.post("/api/v1/query", json={"query": "What is Priya Nandakumar's address?"})
        assert q4_res.status_code == 200
        a4 = q4_res.json()["answer"]
        assert "No address record was found" in a4 or "not find matching records" in a4


