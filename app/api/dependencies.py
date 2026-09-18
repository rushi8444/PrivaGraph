"""FastAPI dependency injection — shared application state."""

from __future__ import annotations

from app.graph.graph_builder import KnowledgeGraphBuilder
from app.tokenization.tokenizer import DeterministicTokenizer
from app.tokenization.vault import EncryptedVault
from app.detection.presidio_engine import PresidioDetectionEngine
from app.retrieval.context_builder import ContextBuilder
from app.retrieval.query_analyzer import QueryAnalyzer
from app.proxy.llm_gateway import LLMGateway
from app.proxy.reconstructor import TokenReconstructor
from app.proxy.prompt_sanitizer import PromptSanitizer
from app.security.audit_log import AuditLogger
from app.ingestion.okf_parser import OKFParser
from app.ingestion.pdf_converter import PDFToOKFConverter
from app.graph.triple_extractor import TripleExtractor
from app.models.auth import UserContext


class AppState:
    """Shared application state holding all pipeline components.

    Created once at startup and injected into route handlers.
    """

    def __init__(self):
        # Stage 1: Ingestion
        self.parser = OKFParser()
        self.pdf_converter = PDFToOKFConverter()

        # Stage 2: Detection & Tokenization
        self.detector: PresidioDetectionEngine | None = None  # Lazy-loaded
        self.tokenizer = DeterministicTokenizer()
        self.vault = EncryptedVault()

        # Stage 3: Knowledge Graph
        self.triple_extractor = TripleExtractor()
        self.graph_builder = KnowledgeGraphBuilder()

        # Stage 4: Retrieval
        self.query_analyzer = QueryAnalyzer()
        self.context_builder = ContextBuilder(
            graph_builder=self.graph_builder,
            query_analyzer=self.query_analyzer,
        )

        # Stage 5: Proxy
        self.llm_gateway = LLMGateway()
        self.reconstructor = TokenReconstructor(self.vault)
        self.sanitizer = PromptSanitizer()

        # Security
        self.audit = AuditLogger()

        # Document registry
        self.documents: dict[str, dict] = {}

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


def get_default_user() -> UserContext:
    """Return a default user context for MVP (no auth required yet)."""
    return UserContext(
        user_id="default",
        username="admin",
        department="Engineering",
    )
