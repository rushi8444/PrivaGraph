import os
os.environ["PYTHONIOENCODING"] = "utf-8"
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=True)

with open("tests/fixtures/doc1_hr_compensation.pdf", "rb") as f:
    r = client.post("/api/v1/documents/ingest", files={"file": ("doc1_hr_compensation.pdf", f, "application/pdf")})
    print("Ingest:", r.status_code)

try:
    resp = client.post("/api/v1/query", json={"query": "What is Priya Nandakumar's Social Security Number?"})
    print("Query:", resp.status_code, resp.text)
except Exception as e:
    import traceback
    traceback.print_exc()
