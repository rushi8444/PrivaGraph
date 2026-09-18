"""Unit tests for row-scoped table parsing, triple extraction, and circuit breakers."""

import pytest

from app.ingestion.table_parser import TableParser
from app.ingestion.okf_parser import OKFParser
from app.graph.triple_extractor import TripleExtractor
from app.graph.graph_builder import KnowledgeGraphBuilder, GraphContaminationError
from app.detection.presidio_engine import PresidioDetectionEngine
from app.tokenization.tokenizer import DeterministicTokenizer
from app.tokenization.vault import EncryptedVault
from app.models.document import OKFHeader, DocumentMeta, Classification, PrivacyConfig, AccessControl, GraphConfig


SAMPLE_5_ROW_TABLE = """---
okf_version: "1.0"
document:
  id: "HR-TEST-001"
  title: "Engineering Compensation Table"
  classification: "CONFIDENTIAL"
  department: "Engineering"
  author: "hr@acme.corp"
  created: "2026-07-15"
privacy:
  entity_categories:
    - PERSON
    - SSN
    - SALARY
  redaction_policy: "TOKENIZE"
  min_confidence: 0.85
access_control:
  allowed_roles:
    - hr_manager
graph:
  namespace: "hr.test"
---

# Compensation Review

| Name | SSN | Salary | Department | Reason |
| --- | --- | --- | --- | --- |
| Priya Nandakumar | 912-04-7731 | $142,500 | Engineering | Merit Raise |
| David Okonkwo | 927-18-3364 | $118,000 | Engineering | Annual Raise |
| Marcus Feldstein | 905-62-1187 | $196,000 | Engineering | Promotion |
| Sarah Johnson | 933-41-8822 | $215,000 | Leadership | Executive Review |
| Elena Rostova | 944-12-5533 | $165,000 | Infrastructure | Role Adjustment |
"""


class TestTableExtraction:
    """Tests isolating table-to-triple generation on a 5-row table."""

    def test_table_parser_isolates_rows(self):
        """Verify TableParser produces row-scoped sentences without cross-row contamination."""
        parser = TableParser()
        tables = parser.parse_markdown_tables(SAMPLE_5_ROW_TABLE)
        assert len(tables) == 1
        table = tables[0]
        assert len(table.rows) == 5

        # Inspect Priya's row
        priya = table.rows[0]
        assert priya.subject == "Priya Nandakumar"
        assert priya.properties["HAS_SSN"] == "912-04-7731"
        assert priya.properties["HAS_SALARY"] == "$142,500"
        assert priya.properties["HAS_REASON"] == "Merit Raise"

        # Inspect Marcus's row
        marcus = table.rows[2]
        assert marcus.subject == "Marcus Feldstein"
        assert marcus.properties["HAS_SSN"] == "905-62-1187"
        assert marcus.properties["HAS_SALARY"] == "$196,000"
        assert marcus.properties["HAS_REASON"] == "Promotion"

        sentences = parser.table_to_row_sentences(table)
        assert len(sentences) == 20  # 5 rows * 4 properties each

        # Confirm Priya's sentences mention only Priya
        priya_sents = [s for s in sentences if "Priya Nandakumar" in s]
        assert len(priya_sents) == 4
        for s in priya_sents:
            assert "David Okonkwo" not in s
            assert "Marcus Feldstein" not in s
            assert "118,000" not in s
            assert "196,000" not in s

    @pytest.mark.asyncio
    async def test_5_row_table_full_ingestion_has_no_cross_contamination(self):
        """Verify full ingestion on a 5-row table yields ~4 properties per person and zero cross-links."""
        okf_parser = OKFParser()
        doc = okf_parser.parse_text(SAMPLE_5_ROW_TABLE, source_path="test_table.md")

        detector = PresidioDetectionEngine()
        tokenizer = DeterministicTokenizer()
        vault = EncryptedVault()
        extractor = TripleExtractor()
        graph_builder = KnowledgeGraphBuilder()

        all_triples = []
        for sentence in doc.sentences:
            entities = detector.detect(sentence)
            tok_text, tok_entities = tokenizer.tokenize_text(sentence, entities)
            for tok in tok_entities:
                await vault.store(
                    token=tok.token,
                    entity_type=tok.entity_type,
                    original_value=tok.original_value,
                    hmac_digest=tok.hmac_digest,
                    doc_id="test_table",
                )
            triples = extractor.extract(tok_text, doc_id="test_table")
            all_triples.extend(triples)

        graph_builder.add_triples(all_triples, doc.header)
        graph = graph_builder.graph

        # Reverse-resolve token nodes to verify edges
        token_map = {tok.token: tok.original_value for tok in tokenizer.tokenize_text(SAMPLE_5_ROW_TABLE, detector.detect(SAMPLE_5_ROW_TABLE))[1]}

        # Check degree per entity: each person should have ~3-4 edges, NOT dozens
        person_tokens = [tok for tok, orig in token_map.items() if orig in ["Priya Nandakumar", "David Okonkwo", "Marcus Feldstein"]]
        assert len(person_tokens) >= 3

        for p_token in person_tokens:
            degree = graph.degree(p_token)
            assert degree <= 6, f"Entity {token_map.get(p_token, p_token)} degree is {degree}, expected <= 6"

            # Check neighbors
            neighbors = list(graph.successors(p_token))
            neighbor_values = [token_map.get(n, n) for n in neighbors]
            orig_name = token_map.get(p_token, "")

            if orig_name == "Priya Nandakumar":
                assert "912-04-7731" in neighbor_values
                assert "$142,500" in neighbor_values
                # Crucial: NO values from David or Marcus
                assert "927-18-3364" not in neighbor_values
                assert "905-62-1187" not in neighbor_values
                assert "$118,000" not in neighbor_values
                assert "$196,000" not in neighbor_values

            elif orig_name == "Marcus Feldstein":
                assert "905-62-1187" in neighbor_values
                assert "$196,000" in neighbor_values
                assert "912-04-7731" not in neighbor_values
                assert "$142,500" not in neighbor_values

    def test_circuit_breaker_triggers_on_explosion(self):
        """Verify circuit breaker raises GraphContaminationError if entity exceeds limit."""
        builder = KnowledgeGraphBuilder(max_edges_per_entity=10)
        header = OKFHeader(
            document=DocumentMeta(
                id="TEST",
                title="T",
                classification=Classification.INTERNAL,
                department="D",
                author="A",
                created="2026-07-15",
            ),
            privacy=PrivacyConfig(entity_categories=[]),
            graph=GraphConfig(namespace="test"),
        )

        from app.graph.triple_extractor import Triple
        exploding_triples = [
            Triple(subject="PersonX", predicate=f"PROP_{i}", object=f"Val_{i}")
            for i in range(15)
        ]

        with pytest.raises(GraphContaminationError, match="circuit breaker triggered"):
            builder.add_triples(exploding_triples, header)
