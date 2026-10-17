"""Unit tests for CSV ingestion."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.ingestion.csv_converter import CSVToOKFConverter
from app.main import app

CSV_BYTES = (
    b"Name,Role,Email,Salary\n"
    b"Alice Johnson,Engineer,alice@example.com,$120000\n"
    b"Bob Smith,Manager,bob@example.com,$150000\n"
)


def test_csv_converter_builds_row_scoped_sentences():
    doc = CSVToOKFConverter().convert(CSV_BYTES, filename="staff.csv", department="Eng")
    assert doc.header.document.id.startswith("CSV-STAFF-")
    assert doc.header.document.department == "Eng"
    assert "Alice Johnson has email alice@example.com." in doc.sentences
    assert "Bob Smith earns $150000." in doc.sentences


def test_csv_converter_rejects_empty_and_headerless():
    conv = CSVToOKFConverter()
    with pytest.raises(ValueError):
        conv.convert(b"", filename="e.csv")
    with pytest.raises(ValueError):
        conv.convert(b"Name,Role\n", filename="h.csv")


@pytest.mark.asyncio
async def test_csv_upload_via_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = {"file": ("staff.csv", CSV_BYTES, "text/csv")}
        response = await ac.post("/api/v1/documents/ingest", files=files)
        assert response.status_code == 200
        result = response.json()
        assert result["doc_id"].startswith("CSV-")
        assert result["triples_extracted"] > 0
