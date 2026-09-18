"""Unit tests for the AnswerSynthesizer and query answering."""

import pytest

from app.retrieval.synthesizer import AnswerSynthesizer


MOCK_GRAPH_CONTEXT = """# Knowledge Graph Context

## Entities
- Priya Nandakumar (namespace: hr.test)
- 912-04-7731 (namespace: hr.test)
- $142,500 (namespace: hr.test)
- Marcus Feldstein (namespace: hr.test)
- 905-62-1187 (namespace: hr.test)
- $196,000 (namespace: hr.test)
- Promotion (namespace: hr.test)

## Relationships
- Priya Nandakumar --[HAS_SSN]--> 912-04-7731
- Priya Nandakumar --[HAS_SALARY]--> $142,500
- Marcus Feldstein --[HAS_SSN]--> 905-62-1187
- Marcus Feldstein --[HAS_SALARY]--> $196,000
- Marcus Feldstein --[HAS_REASON]--> Promotion
"""


class TestAnswerSynthesizer:
    """Tests for query-aware AnswerSynthesizer."""

    def setup_method(self):
        self.synthesizer = AnswerSynthesizer()

    def test_single_property_ssn_lookup(self):
        """Query for Priya's SSN returns only her SSN, not salary or Marcus's SSN."""
        query = "What is Priya Nandakumar's SSN?"
        answer = self.synthesizer.synthesize(query, MOCK_GRAPH_CONTEXT)

        assert "912-04-7731" in answer
        assert "Priya Nandakumar" in answer
        assert "$142,500" not in answer
        assert "905-62-1187" not in answer
        assert "--[" not in answer  # Never raw triples

    def test_single_property_salary_lookup(self):
        """Query for Marcus's salary returns only his salary."""
        query = "What is Marcus Feldstein's salary?"
        answer = self.synthesizer.synthesize(query, MOCK_GRAPH_CONTEXT)

        assert "$196,000" in answer
        assert "Marcus Feldstein" in answer
        assert "$142,500" not in answer
        assert "905-62-1187" not in answer

    def test_present_reason_lookup(self):
        """Query for reason that is present in the graph returns the correct reason."""
        query = "What is the reason for Marcus Feldstein's compensation?"
        answer = self.synthesizer.synthesize(query, MOCK_GRAPH_CONTEXT)

        assert "Promotion" in answer
        assert "Marcus Feldstein" in answer

    def test_absent_property_reports_not_found_honestly(self):
        """Query for a property that is absent for Priya honestly reports absent."""
        query = "What is the reason for Priya Nandakumar's compensation?"
        answer = self.synthesizer.synthesize(query, MOCK_GRAPH_CONTEXT)

        assert "No compensation reason record was found for Priya Nandakumar" in answer
        assert "Promotion" not in answer  # Did not borrow Marcus's reason

    def test_list_aggregation_query(self):
        """List query formats clean bulleted list instead of raw triples."""
        query = "List all employees and their SSNs"
        answer = self.synthesizer.synthesize(query, MOCK_GRAPH_CONTEXT)

        assert "- **Priya Nandakumar**: SSN 912-04-7731" in answer
        assert "- **Marcus Feldstein**: SSN 905-62-1187" in answer
        assert "--[" not in answer

    def test_empty_or_missing_context_never_returns_empty_string(self):
        """Empty context returns polite not-found message, never empty string."""
        empty_answer = self.synthesizer.synthesize("What is Priya's SSN?", "")
        assert empty_answer != ""
        assert "could not find matching records" in empty_answer
