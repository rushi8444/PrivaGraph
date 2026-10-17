"""Unit tests for vault and graph persistence."""

import tempfile
from pathlib import Path
import pytest

from app.security.encryption import AESGCMCipher
from app.tokenization.vault import EncryptedVault
from app.graph.graph_builder import KnowledgeGraphBuilder
from app.graph.triple_extractor import Triple
from app.models.document import OKFHeader, DocumentMeta, Classification, PrivacyConfig, GraphConfig


@pytest.mark.asyncio
async def test_vault_sqlite_persistence():
    """Verify that vault entries survive restart by reloading from SQLite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_vault.db"
        cipher = AESGCMCipher.generate_key()
        aes_cipher = AESGCMCipher(cipher)

        # 1. Initialize vault and store encrypted tokens
        vault1 = EncryptedVault(cipher=aes_cipher, db_path=db_path)
        await vault1.store(
            token="⟦E7_PERSON_001⟧",
            entity_type="PERSON",
            original_value="Alice Smith",
            hmac_digest="digest_alice",
            doc_id="doc_1",
        )
        await vault1.store(
            token="⟦B1_SALARY_001⟧",
            entity_type="SALARY",
            original_value="$150,000",
            hmac_digest="digest_salary",
            doc_id="doc_1",
        )

        assert vault1.count() == 2
        assert await vault1.retrieve("⟦E7_PERSON_001⟧") == "Alice Smith"

        # 2. Simulate server restart: create new vault instance pointing to the same SQLite DB
        vault2 = EncryptedVault(cipher=aes_cipher, db_path=db_path)

        # Confirm all encrypted mappings were loaded from SQLite
        assert vault2.count() == 2
        assert await vault2.retrieve("⟦E7_PERSON_001⟧") == "Alice Smith"
        assert await vault2.retrieve("⟦B1_SALARY_001⟧") == "$150,000"

        # 3. Test deletion by doc_id updates SQLite
        deleted = vault2.delete_by_doc_id("doc_1")
        assert deleted == 2
        assert vault2.count() == 0

        # 4. Verify SQLite file is empty on reload
        vault3 = EncryptedVault(cipher=aes_cipher, db_path=db_path)
        assert vault3.count() == 0


def test_graph_json_persistence():
    """Verify that knowledge graph topology survives restart by reloading from disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_path = Path(tmpdir) / "test_graph.json"

        # 1. Build graph and add triples
        builder1 = KnowledgeGraphBuilder(persist_path=graph_path)
        header = OKFHeader(
            document=DocumentMeta(
                id="doc_1",
                title="Test Doc",
                classification=Classification.INTERNAL,
                department="Engineering",
                author="test",
                created="2026-07-15",
            ),
            privacy=PrivacyConfig(entity_categories=[]),
            graph=GraphConfig(namespace="test"),
        )

        triples = [
            Triple(subject="⟦E7_PERSON_001⟧", predicate="IN_DEPARTMENT", object="Engineering", doc_id="doc_1"),
            Triple(subject="⟦E7_PERSON_001⟧", predicate="REPORTS_TO", object="⟦E7_PERSON_002⟧", doc_id="doc_1"),
        ]
        builder1.add_triples(triples, header)

        assert builder1.graph.number_of_nodes() == 3
        assert builder1.graph.number_of_edges() == 2
        assert graph_path.exists()

        # 2. Simulate server restart: create new builder pointing to the same JSON file
        builder2 = KnowledgeGraphBuilder(persist_path=graph_path)

        assert builder2.graph.number_of_nodes() == 3
        assert builder2.graph.number_of_edges() == 2
        assert builder2.graph.has_edge("⟦E7_PERSON_001⟧", "Engineering")

        # 3. Remove document and verify persistence updates
        builder2.remove_document("doc_1")
        assert builder2.graph.number_of_nodes() == 0

        builder3 = KnowledgeGraphBuilder(persist_path=graph_path)
        assert builder3.graph.number_of_nodes() == 0
