import httpx
import time

time.sleep(2)  # Wait for any reload to finish

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60.0)

# Check health or docs
with open("tests/fixtures/doc1_hr_compensation.pdf", "rb") as f:
    r = client.post("/api/v1/documents/ingest", files={"file": ("doc1_hr_compensation.pdf", f, "application/pdf")})
    print("Ingest status:", r.status_code)
    print("Ingest json:", r.json())

resp = client.post("/api/v1/query", json={"query": "What is Priya Nandakumar's Social Security Number?"})
print("Query status:", resp.status_code)
print("Query response:", resp.json())
