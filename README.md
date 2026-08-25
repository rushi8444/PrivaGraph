# PrivaGraph 🛡️

> **Secure Knowledge Graph Proxy & Privacy-Preserving RAG Middleware for Enterprise LLMs**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5+-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![Encryption](https://img.shields.io/badge/Security-AES--256--GCM-blue.svg)](#security--privacy-architecture)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📖 Overview

**PrivaGraph** is a local security middleware proxy that sits between your enterprise files and cloud AI models (OpenAI, Anthropic Claude, Gemini).

Instead of sending raw confidential text containing Personally Identifiable Information (PII), salaries, or trade secrets to external APIs, PrivaGraph:
1. Detects and extracts sensitive entities from documents.
2. Replaces them with **deterministic opaque tokens** (e.g., `⟦E7_PERSON_001⟧`, `⟦B1_SALARY_002⟧`).
3. Stores the real values in a local **AES-256-GCM encrypted vault**.
4. Builds an **anonymized Knowledge Graph** with role-based access controls (RBAC).
5. Passes only the sanitized subgraph context to cloud LLMs.
6. **Locally reconstructs** the returned answer with decrypted values before showing it to the authorized user.

---

## ⚡ Architecture Flow

```
[Enterprise OKF Documents]
            │
            ▼ (Stage 1: Ingestion & Validation)
[OKF Frontmatter Parser & Schema Registry]
            │
            ▼ (Stage 2: PII Detection & Tokenization)
[Presidio / Fallback NER] ──► [Deterministic HMAC Tokenizer] ──► [AES-256-GCM Vault (Local)]
            │
            ▼ (Stage 3: Graph Construction)
[SVO Triple Extractor] ──► [NetworkX Knowledge Graph]
            │
            ▼ (Stage 4: Retrieval & Security Filtering)
[RBAC Subgraph Filter] ──► [OWASP Prompt Sanitizer]
            │
            ▼ (Stage 5: External LLM Proxy & Local Reconstruction)
[Cloud LLM Gateway] (Anonymized Tokens Only)
            │
            ▼
[Local Token Reconstructor] ──► [Decrypted Answer to User]
```

---

## ✨ Features

- 🔒 **Zero PII Cloud Exposure**: Cloud LLMs only receive abstract graph structures with opaque tokens.
- 🔑 **Deterministic Tokenization**: Identical entities across documents receive identical tokens, allowing cross-document graph linking without exposing real identities.
- 🛡️ **Encrypted Local Vault**: All token-to-PII mappings are protected with authenticated AES-256-GCM encryption.
- 👥 **Fine-Grained RBAC**: Graph nodes and edges inherit document security levels (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`) and allowed/denied role lists.
- 🛑 **OWASP Prompt Injection Defense**: Real-time context scanner that detects and blocks instruction overrides, role hijacking, and exfiltration attempts.
- 📜 **Tamper-Evident Audit Logging**: Cryptographically hash-chained audit log recording all ingestion, queries, vault accesses, and blocked attacks.
- 💻 **Modern React Dashboard**: Dark-mode interface with Query Chat, drag-and-drop OKF document uploader, D3.js interactive force-directed graph canvas, and audit trail viewer.

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
> *Note: If no API key is provided, PrivaGraph automatically runs in offline graph-retrieval fallback mode for local testing!*

---

### 2. Backend Setup (FastAPI)

```bash
# Install backend dependencies
pip install -e .

# Or install manually via requirements / pip
pip install fastapi uvicorn cryptography pydantic-settings python-dotenv pyyaml httpx networkx pytest pytest-asyncio
```

Run the backend server:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Server: `http://localhost:8000`
- Interactive Swagger Docs: `http://localhost:8000/docs`

---

### 3. Frontend Setup (React + Vite)

In a new terminal window:

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

Run the complete test suite (unit tests + full end-to-end API integration tests):

```bash
python -m pytest tests/ -v
```

---

## 📂 Project Structure

```
privacy-guard/
├── app/
│   ├── api/                  # FastAPI routes & dependency injection
│   │   └── v1/               # /documents, /query, /graph, /admin endpoints
│   ├── detection/            # Presidio NER engine & custom domain recognizers
│   ├── graph/                # Triple extractor & NetworkX knowledge graph
│   ├── ingestion/            # OKF Markdown parser & schema registry
│   ├── models/               # Pydantic schemas (document, entity, graph, query)
│   ├── proxy/                # LLM gateway, prompt sanitizer, local reconstructor
│   ├── retrieval/            # RBAC filter, query analyzer, context builder
│   ├── security/             # AES-256-GCM encryption, vault, hash-chained audit log
│   ├── tokenization/         # Deterministic HMAC tokenizer & token codec
│   ├── config.py             # Pydantic Settings configuration
│   └── main.py               # FastAPI entry point
│
├── frontend/                 # React 18 + Vite Web Dashboard
│   ├── src/
│   │   ├── api/              # API client with Vite proxy
│   │   ├── components/       # Layout, ChatPanel, DocumentUploader, D3 GraphCanvas
│   │   ├── pages/            # Query, Documents, Graph, and Audit pages
│   │   ├── App.jsx           # React Router shell
│   │   └── index.css         # Dark-mode design system
│   ├── index.html
│   └── vite.config.js
│
├── tests/
│   ├── fixtures/             # Sample OKF Markdown documents (HR, Finance, Malicious)
│   └── unit/                 # Unit & integration test suites
│
├── pyproject.toml
└── README.md
```

---

## 📄 Open Knowledge Format (OKF) Spec

PrivaGraph uses Markdown files with structured YAML frontmatter:

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
access_control:
  allowed_roles:
    - hr_manager
    - cfo
  denied_roles:
    - intern
graph:
  namespace: "hr.compensation"
  link_strategy: "cross_document"
  max_traversal_depth: 3
---

# Q3 Compensation Review

John Smith (SSN: 123-45-6789) is a Senior Engineer earning $185,000/year.
He manages a team budget of $2.3M and reports to Sarah Johnson (VP Engineering).
```

---

## 🔌 API Reference Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/ingest` | Upload & ingest OKF document (parse, tokenize, build graph) |
| `GET` | `/api/v1/documents` | List all ingested document metadata |
| `POST` | `/api/v1/query` | Submit natural language query through privacy proxy |
| `GET` | `/api/v1/graph/nodes` | Retrieve full tokenized knowledge graph for visualization |
| `GET` | `/api/v1/graph/stats` | Summary statistics (node count, edge count, namespaces) |
| `GET` | `/api/v1/admin/audit-log` | View cryptographically verified tamper-evident audit trail |
| `GET` | `/api/v1/health` | Middleware health check |

---

## 🛡️ Security & Privacy Guarantees

- **No Plaintext PII Transmission**: Real entity values are stripped and tokenized locally before sending requests over the network.
- **OWASP LLM Top 10 Mitigation**:
  - *LLM01 (Prompt Injection)*: Context is scanned with pattern analysis prior to prompt assembly.
  - *LLM02 (Sensitive Information Disclosure)*: Output filter scans answers for accidental disclosures.
  - *LLM06 (Excessive Agency)*: Strict read-only RBAC graph boundaries.
- **Cryptographic Auditability**: Every operation is chained with SHA-256 hashes (`entry_hash = SHA-256(entry + prev_hash)`).

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.
