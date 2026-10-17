"""Unit and integration tests for asynchronous background ingestion and job progress tracking."""

from pathlib import Path
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_async_document_ingestion_and_job_tracking():
    """Verify that background document ingestion returns 202 Accepted and completes with progress updates."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        sample_file = FIXTURES_DIR / "sample_hr_doc.md"
        with open(sample_file, "rb") as f:
            files = {"file": ("sample_hr_doc.md", f, "text/markdown")}
            data = {"background": "true"}
            res = await ac.post("/api/v1/documents/ingest", files=files, data=data)

        # 1. Immediate 202 Accepted response with job tracking metadata
        assert res.status_code == 202
        body = res.json()
        assert body["status"] == "processing"
        assert "job_id" in body
        job_id = body["job_id"]
        assert body["check_status_url"] == f"/api/v1/documents/jobs/{job_id}"

        # 2. Poll job status until completion (or timeout)
        completed = False
        final_job = None
        for _ in range(30):
            status_res = await ac.get(f"/api/v1/documents/jobs/{job_id}")
            assert status_res.status_code == 200
            job_data = status_res.json()
            if job_data["status"] == "completed":
                completed = True
                final_job = job_data
                break
            await asyncio.sleep(0.1)

        assert completed, f"Job {job_id} did not complete in time"
        assert final_job["stage"] == "completed"
        assert final_job["progress_pct"] == 100
        assert final_job["result"] is not None
        assert final_job["result"]["status"] == "ingested"
        doc_id = final_job["result"]["doc_id"]

        # 3. Verify document exists in document registry
        doc_res = await ac.get(f"/api/v1/documents/{doc_id}")
        assert doc_res.status_code == 200
        assert doc_res.json()["id"] == doc_id

        # 4. Verify job appears in list_jobs
        list_jobs_res = await ac.get("/api/v1/documents/jobs")
        assert list_jobs_res.status_code == 200
        jobs_list = list_jobs_res.json()["jobs"]
        assert any(j["job_id"] == job_id for j in jobs_list)


@pytest.mark.asyncio
async def test_job_not_found_returns_404():
    """Verify non-existent job ID returns 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/documents/jobs/job_nonexistent_999")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_async_unsupported_format_rejected_immediately():
    """Verify unsupported formats fail fast with 400 even when background=true is passed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = {"file": ("unsupported.exe", b"binary_executable_data", "application/octet-stream")}
        data = {"background": "true"}
        res = await ac.post("/api/v1/documents/ingest", files=files, data=data)
        assert res.status_code == 400
        assert "Unsupported file format" in res.json()["detail"]
