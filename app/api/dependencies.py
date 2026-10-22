"""FastAPI dependency injection — shared application state."""

from __future__ import annotations

from app.graph.graph_store import FileGraphStore, Neo4jGraphStore
from app.tokenization.tokenizer import DeterministicTokenizer
from app.tokenization.vault import EncryptedVault
from app.detection.presidio_engine import PresidioDetectionEngine
from app.retrieval.context_builder import ContextBuilder
from app.retrieval.query_analyzer import QueryAnalyzer
from app.retrieval.passage_store import PassageStore
from app.proxy.llm_gateway import LLMGateway
from app.proxy.reconstructor import TokenReconstructor
from app.proxy.prompt_sanitizer import PromptSanitizer
from app.security.audit_log import AuditLogger
from app.ingestion.okf_parser import OKFParser
from app.ingestion.pdf_converter import PDFToOKFConverter
from app.ingestion.csv_converter import CSVToOKFConverter
from app.graph.triple_extractor import TripleExtractor
from app.models.auth import UserContext


import json
import uuid
from datetime import datetime, timezone
from app.config import settings

class AppState:
    """Shared application state holding all pipeline components.

    Created once at startup and injected into route handlers.
    """

    def __init__(self):
        # Stage 1: Ingestion
        self.parser = OKFParser()
        self.pdf_converter = PDFToOKFConverter()
        self.csv_converter = CSVToOKFConverter()

        # Stage 2: Detection & Tokenization
        self.detector: PresidioDetectionEngine | None = None  # Lazy-loaded
        self.tokenizer = DeterministicTokenizer()
        self.vault = EncryptedVault(db_path=settings.DATA_DIR / "vault.db")

        # Stage 3: Knowledge Graph
        self.triple_extractor = TripleExtractor()
        if settings.GRAPH_BACKEND == "neo4j":
            self.graph_builder = Neo4jGraphStore(
                settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        else:
            self.graph_builder = FileGraphStore(settings.DATA_DIR / "graph.json")

        # Stage 4: Retrieval
        self.query_analyzer = QueryAnalyzer()
        self.passage_store = PassageStore(settings.DATA_DIR / "passages.sqlite3")
        self.context_builder = ContextBuilder(
            graph_builder=self.graph_builder,
            query_analyzer=self.query_analyzer,
            passage_store=self.passage_store,
        )

        # Stage 5: Proxy
        self.llm_gateway = LLMGateway()
        self.reconstructor = TokenReconstructor(self.vault)
        self.sanitizer = PromptSanitizer()

        # Security
        self.audit = AuditLogger()

        # Document registry (persisted to data/documents.json)
        self.documents: dict[str, dict] = self._load_documents()

        # Asynchronous ingestion job registry
        self.jobs: dict[str, dict] = {}

    def create_job(self, filename: str) -> str:
        """Create and register a new asynchronous ingestion job."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        self.jobs[job_id] = {
            "job_id": job_id,
            "filename": filename,
            "status": "queued",
            "stage": "queued",
            "progress_pct": 0,
            "error": None,
            "result": None,
            "created_at": now,
            "updated_at": now,
        }
        return job_id

    def update_job(
        self,
        job_id: str,
        status: str,
        stage: str,
        progress_pct: int,
        error: str | None = None,
        result: dict | None = None,
    ) -> None:
        """Update job stage, completion percentage, and execution status."""
        if job_id in self.jobs:
            self.jobs[job_id].update({
                "status": status,
                "stage": stage,
                "progress_pct": progress_pct,
                "error": error,
                "result": result,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

    def get_job(self, job_id: str) -> dict | None:
        """Retrieve job status dictionary by job ID."""
        return self.jobs.get(job_id)

    def list_jobs(self) -> list[dict]:
        """List all tracked ingestion jobs sorted by creation timestamp."""
        return sorted(self.jobs.values(), key=lambda j: j.get("created_at", ""), reverse=True)

    def _load_documents(self) -> dict[str, dict]:
        """Load document metadata registry from disk."""
        doc_path = settings.DATA_DIR / "documents.json"
        if doc_path.exists():
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_documents(self) -> None:
        """Persist document metadata registry to disk."""
        doc_path = settings.DATA_DIR / "documents.json"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(doc_path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2)
        except Exception:
            pass

    def reset_state(self) -> None:
        """Completely reset in-memory and persistent state for clean test runs."""
        self.graph_builder.clear()
        self.passage_store.clear()
        self.vault.clear()
        self.documents.clear()
        self.jobs.clear()
        self.save_documents()

    def get_detector(self) -> PresidioDetectionEngine:
        """Lazy-load the Presidio detection engine (heavy spaCy model)."""
        if self.detector is None:
            self.detector = PresidioDetectionEngine()
        return self.detector


# Singleton application state
app_state = AppState()


def get_state() -> AppState:
    """Get the shared application state."""
    return app_state


from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def get_default_user() -> UserContext:
    """Return a default user context for fallback."""
    return UserContext(
        user_id="usr_default",
        username="admin",
        email="admin@privagraph.local",
        department="Engineering",
    )


async def get_current_user_or_default(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserContext:
    """Return authenticated user if Bearer token present, else default user context."""
    if credentials and credentials.credentials:
        from app.api.v1.auth import get_current_user_with_token

        user_ctx, _, _, _ = await get_current_user_with_token(credentials)
        return user_ctx
    return get_default_user()


from app.api.v1.auth import get_current_user, get_current_user_with_token
