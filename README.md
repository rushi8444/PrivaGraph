# PrivaGraph 🛡️

> **Secure Knowledge Graph Proxy & Privacy-Preserving RAG Middleware for Enterprise LLMs**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5+-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.24+-red.svg)](https://pymupdf.readthedocs.io)
[![Tests](https://img.shields.io/badge/Tests-47%20Passed-brightgreen.svg)](#-running-automated-tests)
[![Encryption](https://img.shields.io/badge/Security-AES--256--GCM-blue.svg)](#-security--privacy-architecture)

---

## 📖 Overview

**PrivaGraph** is an enterprise security middleware proxy and Graph-RAG engine that sits between your confidential internal documents and cloud AI models (OpenAI GPT-4o, Anthropic Claude, Google Gemini).

Instead of sending raw confidential text containing Personally Identifiable Information (PII), compensation figures, social security numbers, or internal organizational charts to external APIs, PrivaGraph:
1. **Multi-Format Ingestion**: Ingests enterprise documents in both **Open Knowledge Format (OKF) Markdown** and **native PDF** formats via PyMuPDF.
2. **Anti-Cartesian Table Isolation**: Parses structured markdown and delimited text tables into strictly row-scoped sentences, preventing cross-row entity contamination and combinatorial graph explosion.
3. **PII Detection & Tokenization**: Detects and extracts sensitive entities using Microsoft Presidio (with regex fallback), replacing them with **deterministic HMAC-SHA256 tokens** (e.g., `⟦E7_PERSON_001⟧`, `⟦B1_SALARY_002⟧`).
4. **Encrypted Local Vault**: Stores real entity values in a local **AES-256-GCM authenticated vault** with random 96-bit nonces.
5. **Enterprise Knowledge Graph**: Builds an anonymized multi-document **NetworkX Knowledge Graph** tagged with classification levels (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`).
6. **Multi-Hop Traversal & Department Boundary Filtering**: Extracts k-hop subgraphs with strict organizational boundary controls (e.g., isolating Engineering employees without leaking Sales or Finance).
7. **OWASP Prompt Injection Scanner**: Evaluates sanitized contexts against instruction overrides, role hijacking, exfiltration, and vault probing before cloud dispatch.
8. **Local Answer Reconstruction & Offline Synthesis**: Passes only tokenized subgraph context to the cloud LLM, then locally reconstructs decrypted values—or falls back to a query-aware local **Answer Synthesizer** when operating offline.

---

## ⚡ Architecture Flow

```
[Enterprise Documents: OKF Markdown / Native PDF]
                        │
                        ▼ (Stage 1: Ingestion & Table Isolation)
    [PyMuPDF PDF Converter & TableParser (Anti-Cartesian Engine)]
                        │
                        ▼ (Stage 2: PII Detection & Tokenization)
    [Presidio / Fallback NER] ──► [HMAC-SHA256 Tokenizer] ──► [AES-256-GCM Vault (Local)]
                        │
                        ▼ (Stage 3: Graph Construction & Alias Normalization)
    [SVO Triple Extractor] ──► [NetworkX Knowledge Graph (MultiDiGraph)]
                        │
                        ▼ (Stage 4: Query Retrieval & Multi-Hop BFS)
    [Department Filter & Multi-Hop BFS] ─────────────────────────────► [OWASP Sanitizer]
                        │
                        ▼ (Stage 5: LLM Proxying / Local Answer Synthesis)
    [Cloud LLM Gateway] (Tokens Only)  OR  [Local Query-Aware Answer Synthesizer]
                        │
                        ▼
    [Local Token Reconstructor (AES Decryption)] ──► [Decrypted Natural Language Answer]
```

---

## ✨ Features

- 🔒 **Zero PII Cloud Exposure**: Cloud LLMs only ever see abstract graph topology and opaque tokens (`⟦E7_PERSON_001⟧`). Master encryption keys and raw PII never leave the enterprise perimeter.
- 📄 **Native PDF & OKF Ingestion**: Ingests both structured `.md` files with YAML frontmatter and native `.pdf` files. Automatically extracts text, extracts tables, and synthesizes full OKF headers.
- 📊 **Anti-Cartesian Table Parser**: Isolates table rows into independent subject-property pairs to prevent cross-contamination (e.g., employee A's SSN never associates with employee B's salary) with built-in circuit-breaker thresholds.
- 🔑 **Deterministic Tokenization**: Keyed HMAC-SHA256 ensures identical entities across distinct documents produce the exact same token, enabling rich cross-document graph linkage.
- 🏷️ **Alias & Compound Surname Resolution**: Normalizes hyphenated surnames (e.g., *Harold Mbeki-Sorensen* vs. *Harold Mbeki*) to the same canonical token while upgrading vault entries with full names.
- 🏢 **Department Boundary Filtering**: Restricts query context strictly to the target department (e.g., Engineering) without leaking personnel from Sales, Finance, or Executive tiers.
- 🔗 **Multi-Hop Hierarchy Traversal**: Traverses organizational reporting lines (e.g., "Who does X report to, and who does that person report to?").
- 🧠 **Query-Aware Answer Synthesizer**: Produces concise, direct answers for specific property lookups (SSN, salary, address, promotions), honest reporting of absent facts, and provides high-fidelity offline fallback.
- 🛑 **OWASP LLM Top 10 Mitigation**: Proactively neutralizes prompt injections, system prompt extraction, role hijacking, and vault key probing.
- 📜 **Tamper-Evident Audit Trail**: Cryptographic SHA-256 hash-chaining (`entry_hash = SHA-256(data + prev_hash)`) records every ingestion, query, and security event.
- 💻 **Modern React Dashboard**: Dark-mode interface with natural language Query Chat, drag-and-drop file uploader (MD & PDF), interactive D3.js force-directed graph canvas, and audit trail viewer.

---

## 🚀 Quick Setup & Run

### Prerequisites
- **Python 3.11+** installed
- **Node.js 18+** and `npm` installed

---

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/your-org/privacy-guard.git
cd privacy-guard

# Copy the environment file template
cp .env.example .env
```

*(Optional)* Configure your LLM provider API key in `.env`:
```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
DEFAULT_MODEL=gpt-4o
```
> **Note:** If no external API key is provided or the cloud model is unreachable, PrivaGraph automatically activates its local **Answer Synthesizer** for offline testing and evaluation!

---

### 2. Backend Setup (FastAPI)

```bash
# Install backend in editable mode (including PyMuPDF, Presidio, Cryptography, NetworkX)
pip install -e .

# Or install dependencies directly via pip:
pip install fastapi uvicorn cryptography pydantic-settings python-dotenv pyyaml httpx networkx pymupdf presidio-analyzer presidio-anonymizer spacy pytest pytest-asyncio
```

Run the FastAPI server:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Server: `http://localhost:8000`
- Interactive OpenAPI / Swagger Docs: `http://localhost:8000/docs`

---

### 3. Frontend Setup (React + Vite)

In a separate terminal:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

- Web Dashboard: **`http://localhost:3000`**

---

## 🧪 Running Automated Tests

PrivaGraph includes a complete automated test suite of **47 unit, integration, and regression tests**:

```bash
# Run all tests with verbose output
python -m pytest tests/ -v
```

### Test Suite Coverage:
- **`tests/unit/test_api.py`**: End-to-end API lifecycle (Markdown ingestion, PDF upload, query retrieval, table isolation, format validation).
- **`tests/unit/test_okf_parser.py`**: Frontmatter validation, YAML error handling, sentence segmentation.
- **`tests/unit/test_pdf_converter.py`**: PyMuPDF extraction, metadata overrides, raw byte streams, corrupt/empty PDF rejection.
- **`tests/unit/test_table_triples.py`**: Anti-cartesian row isolation, header-to-predicate normalization, circuit breaker limits.
- **`tests/unit/test_tokenizer.py`**: Deterministic HMAC generation, collision avoidance, offset-safe string tokenization.
- **`tests/unit/test_prompt_sanitizer.py`**: OWASP injection defense (instruction overrides, role hijacking, vault probing).
- **`tests/unit/test_query_synthesis.py`**: Query-aware answer synthesis, single-property lookups, absent record handling.
- **`tests/unit/test_retrieval_fixes.py`**: 6 real-world benchmark regression tests (SSN lookup, department boundaries, compound alias normalization, multi-hop reporting chains, promotion reasons, executive retention terms).
- **`tests/unit/test_reconstructor.py`**: AES-256-GCM vault decryption and in-place token replacement.

---

## 📂 Project Structure

```
privacy-guard/
├── app/
│   ├── api/                  # FastAPI controllers & dependency injection
│   │   ├── dependencies.py   # Shared AppState & UserContext dependencies
│   │   └── v1/               # /documents, /query, /graph, /admin endpoints
│   ├── detection/            # Presidio NER engine & custom domain recognizers
│   │   ├── presidio_engine.py# Presidio engine with regex FallbackPIIDetector
│   │   └── custom_recognizers.py # Salary, SSN, Employee ID, Project Code regexes
│   ├── graph/                # Knowledge Graph & relation extraction
│   │   ├── graph_builder.py  # NetworkX MultiDiGraph manager & graph metrics
│   │   └── triple_extractor.py# SVO parsing, hub-and-spoke linking, coreference
│   ├── ingestion/            # Multi-format document ingestion pipeline
│   │   ├── okf_parser.py     # OKF YAML frontmatter & markdown sentence parser
│   │   ├── pdf_converter.py  # Native PDF text & metadata converter (PyMuPDF)
│   │   ├── table_parser.py   # Row-scoped table parser (anti-cartesian engine)
│   │   └── schema_registry.py# Category & classification validation
│   ├── models/               # Pydantic schemas (documents, entities, graph, query, auth)
│   ├── proxy/                # LLM gateway & privacy proxy
│   │   ├── llm_gateway.py    # OpenAI, Anthropic, Gemini unified gateway
│   │   ├── prompt_sanitizer.py# OWASP prompt injection scanner & vault defense
│   │   └── reconstructor.py  # Local vault decryption & token replacer
│   ├── retrieval/            # Knowledge graph search & answer generation
│   │   ├── context_builder.py# Graph neighborhood assembly & department filter
│   │   ├── query_analyzer.py # Query keyword/token extractor & hyphen expansion
│   │   └── synthesizer.py    # Query-aware local answer synthesizer
│   ├── security/             # Cryptographic security layer
│   │   ├── cipher.py         # AES-256-GCM authenticated encryption/decryption
│   │   ├── audit_log.py      # Tamper-evident SHA-256 hash-chained audit log
│   │   └── trust_boundary.py # Trust zone enforcement (Local vs. Cloud)
│   ├── tokenization/         # Deterministic tokenization & encrypted vault
│   │   ├── tokenizer.py      # HMAC-SHA256 entity tokenizer & alias normalizer
│   │   ├── vault.py          # Encrypted vault storage with value upgrade support
│   │   └── token_codec.py    # Token format encoder/decoder (⟦XX_TYPE_NNN⟧)
│   ├── config.py             # Pydantic Settings configuration
│   └── main.py               # FastAPI application entry point
│
├── frontend/                 # React 18 + Vite Web Dashboard
│   ├── src/
│   │   ├── api/              # Axios/Fetch API client with Vite proxy
│   │   ├── components/       # UI Components (Layout, ChatPanel, Uploader, D3 Graph)
│   │   ├── pages/            # Query, Documents, Graph, and Audit pages
│   │   ├── App.jsx           # Application shell & navigation
│   │   └── index.css         # Dark-mode design system
│   ├── index.html
│   └── vite.config.js
│
├── tests/
│   ├── fixtures/             # Sample OKF Markdown & PDF documents (HR, Finance, Payroll)
│   ├── generate_fixtures.py  # PDF fixture generator
│   └── unit/                 # 47 unit & integration test suites
│
├── pyproject.toml
└── README.md
```

---

## 📄 Open Knowledge Format (OKF) & PDF Ingestion

### 1. OKF Markdown Specification
PrivaGraph supports Markdown files with structured YAML frontmatter:

```markdown
---
okf_version: "1.0"
document:
  id: "HR-2026-00142"
  title: "Q3 Compensation Review"
  classification: "CONFIDENTIAL"
  department: "Human Resources"
  author: "jane.doe@acme.corp"
  created: "2026-07-15"
privacy:
  entity_categories:
    - PERSON
    - SALARY
    - SSN
    - EMAIL
  redaction_policy: "TOKENIZE"
  min_confidence: 0.85
graph:
  namespace: "hr.compensation"
  link_strategy: "cross_document"
  max_traversal_depth: 3
---

# Q3 Compensation Review

Priya Nandakumar (SSN: 912-04-7731) is a Principal Engineer earning $210,000/year.
She works in the Engineering department and reports to Marcus Feldstein.
```

### 2. Native PDF Ingestion
When uploading `.pdf` files, `PDFToOKFConverter` automatically:
- Extracts text content and structural tables across all pages via PyMuPDF.
- Synthesizes document metadata (computing a SHA-256 checksum ID `DOC-<hash>`).
- Infers or applies user-supplied classification, department, and author.
- Injects standard privacy scanning configurations.

---

## 🔌 API Reference Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/ingest` | Upload & ingest document (`.md` or `.pdf`) with optional metadata overrides |
| `GET` | `/api/v1/documents` | List all ingested document metadata, classifications, and departments |
| `POST` | `/api/v1/query` | Submit natural language query through privacy proxy & get reconstructed answer |
| `GET` | `/api/v1/graph/nodes` | Retrieve full tokenized knowledge graph for D3 visualization |
| `GET` | `/api/v1/graph/stats` | Summary statistics (node count, edge count, namespaces, density) |
| `GET` | `/api/v1/admin/audit-log` | Retrieve cryptographically verified tamper-evident audit trail |
| `GET` | `/api/v1/health` | Service health check |

---

## 🛡️ Security & Privacy Guarantees

1. **Zero Plaintext PII Transmission**: Sensitive entity values are tokenized and stored in an encrypted vault locally before network dispatch. External LLMs only receive abstract token identifiers.
2. **OWASP LLM Top 10 Mitigation**:
   - **LLM01 (Prompt Injection)**: Pattern analysis inspects retrieved context for instruction overrides and jailbreaks prior to prompt construction.
   - **LLM02 (Sensitive Information Disclosure)**: AES-256-GCM vault encryption ensures real PII cannot be exposed via prompt leakage.
   - **LLM06 (Excessive Agency)**: Subgraphs are restricted via strict department boundary filtering and multi-hop radius boundaries.
3. **Anti-Cartesian Isolation**: Prevents tabular data from leaking relationships between unrelated entities across rows.
4. **Cryptographic Auditability**: Every operation is logged with an incremental SHA-256 hash chain (`entry_hash = SHA-256(entry + prev_hash)`), ensuring non-repudiation and tamper detection.

---


