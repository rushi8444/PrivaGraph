---
name: code-review-testing
description: >
  Perform structured code review and generate/run tests for the PrivaGraph
  privacy-preserving Graph RAG middleware. Covers FastAPI endpoints, Pydantic
  models, PII tokenization/reconstruction, graph retrieval, and security layers.
  Use when asked to review code, write tests, check coverage, or run the test
  suite for this project.
---

# Code Review & Testing Skill — PrivaGraph

## Project Context

PrivaGraph is a **privacy-preserving Graph RAG middleware** built with:

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Models | Pydantic v2 |
| PII Detection | Microsoft Presidio (spaCy backend) |
| Tokenization/Vault | Custom AES-256-GCM encrypted vault |
| Knowledge Graph | NetworkX (in-memory) + optional Neo4j |
| Auth | JWT (python-jose) + passlib/bcrypt |
| Testing | pytest + pytest-asyncio + hypothesis |
| Linting | ruff (line-length 100, target py311) |
| Type-checking | mypy |

Key directories:
- `app/` — FastAPI application
  - `api/` — Route handlers
  - `models/` — Pydantic request/response models (`query.py`, etc.)
  - `detection/` — PII detection (Presidio wrappers)
  - `tokenization/` — Token vault, anonymization
  - `graph/` — Graph ingestion and traversal
  - `retrieval/` — Subgraph retrieval logic
  - `proxy/` — Cloud LLM proxy (zero-PII egress)
  - `security/` — Auth, JWT utilities
  - `ingestion/` — Document parsers (PDF, XLSX, CSV, OKF)
- `tests/unit/` — All existing unit tests (20 files)
- `tests/fixtures/` — Shared test fixtures
- `tests/conftest.py` — Global pytest configuration

---

## Code Review Checklist

When asked to review code, evaluate against **all** of the following:

### 1. Privacy & Security (Critical — PrivaGraph Core Invariants)
- [ ] No raw PII (names, emails, IDs, etc.) ever leaves the private perimeter unencrypted
- [ ] All tokens passed to the cloud LLM are verified as anonymized (check `ZeroPIIProof`)
- [ ] Vault keys are never logged, returned in API responses, or stored in plaintext
- [ ] Token/entity reconstruction only happens **after** LLM response is received
- [ ] No secrets in code; config comes from `app/config.py` / `.env`
- [ ] Auth-gated endpoints use the correct dependency (FastAPI `Depends`)

### 2. Pydantic Model Hygiene
- [ ] All fields have correct types and `Field(...)` validators where needed
- [ ] Sensitive fields use `SecretStr` or are excluded from serialization via `model_config`
- [ ] Response models never accidentally expose internal fields
- [ ] `from __future__ import annotations` at top of every model file

### 3. API Layer
- [ ] Endpoints return correct HTTP status codes (422 for validation, 401/403 for auth)
- [ ] Async route handlers use `async def`; no blocking I/O in async context
- [ ] File upload handlers clean up temporary files
- [ ] Pagination applied to list endpoints

### 4. Graph Layer
- [ ] `max_traversal_depth` is respected in graph traversal (prevent runaway queries)
- [ ] Neo4j queries use parameterized Cypher (no string interpolation)
- [ ] NetworkX fallback is available when Neo4j is unavailable

### 5. Code Quality
- [ ] Follows ruff rules (line-length <= 100, py311 target)
- [ ] mypy annotations present on all public functions/methods
- [ ] No mutable default arguments
- [ ] Docstrings on all public classes and functions
- [ ] No `print()` statements — use `structlog` for logging

---

## Testing Guidelines

### Running Tests

```bash
# All tests
cd d:\Projects\PrivaGraph
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov=app --cov-report=term-missing -v

# Single file
python -m pytest tests/unit/test_tokenizer.py -v

# Linting
python -m ruff check app/ tests/

# Type checking
python -m mypy app/
```

### Writing New Tests

**File naming:** `tests/unit/test_<module_name>.py`

**Standard test structure for a PrivaGraph unit test:**

```python
"""Tests for app.<module>.<submodule>."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_feature_returns_expected():
    ...


def test_feature_with_empty_input():
    ...


def test_no_pii_in_output():
    """Ensure raw PII never appears in the processed output."""
    ...


def test_feature_raises_on_invalid_input():
    with pytest.raises(ValueError):
        ...
```

**Async test pattern (FastAPI endpoints):**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_query_endpoint(client):
    response = await client.post("/query", json={"query": "test question"})
    assert response.status_code == 200
```

**Property-based testing with Hypothesis (for tokenization/PII logic):**

```python
from hypothesis import given, strategies as st


@given(st.text(min_size=1, max_size=500))
def test_tokenize_is_reversible(text: str):
    tokens, vault = tokenize(text)
    reconstructed = reconstruct(tokens, vault)
    assert reconstructed == text
```

### Coverage Targets

| Module | Target |
|---|---|
| `app/models/` | 100% |
| `app/detection/` | >= 90% |
| `app/tokenization/` | >= 90% |
| `app/api/` | >= 85% |
| `app/graph/` | >= 80% |
| `app/retrieval/` | >= 80% |
| `app/security/` | >= 90% |

---

## Review Workflow

When the user asks to **review a file**:

1. Read the file with `view_file`
2. Run ruff lint check: `python -m ruff check <file> --output-format=text`
3. Run mypy: `python -m mypy <file>`
4. Apply the review checklist above, prioritizing privacy invariants
5. Report findings grouped by: Critical | Warning | Suggestion
6. Offer to auto-fix ruff issues with `python -m ruff check <file> --fix`

When the user asks to **write tests for a file**:

1. Read the source file to understand all public functions/classes
2. Check existing test file (if any) in `tests/unit/`
3. Write tests covering: happy path, edge cases, privacy invariants, error cases
4. Run the new tests to verify they pass
5. Report coverage delta

When the user asks to **run tests**:

1. Run `python -m pytest tests/ -v --tb=short` from `d:\Projects\PrivaGraph`
2. Report failures with full tracebacks
3. Suggest fixes for failing tests
