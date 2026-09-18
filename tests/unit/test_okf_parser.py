"""Unit tests for the OKF parser."""

from pathlib import Path

import pytest

from app.ingestion.okf_parser import OKFParser
from app.models.document import Classification, RedactionPolicy


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestOKFParser:
    """Tests for OKFParser."""

    def setup_method(self):
        self.parser = OKFParser()

    def test_parse_hr_document(self):
        """Parse a valid HR document with full OKF headers."""
        doc = self.parser.parse(FIXTURES_DIR / "sample_hr_doc.md")

        assert doc.header.document.id == "HR-2026-00142"
        assert doc.header.document.title == "Q3 Compensation Review"
        assert doc.header.document.classification == Classification.CONFIDENTIAL
        assert doc.header.document.department == "Human Resources"
        assert doc.header.privacy.redaction_policy == RedactionPolicy.TOKENIZE
        assert doc.header.privacy.min_confidence == 0.85
        assert "PERSON" in doc.header.privacy.entity_categories
        assert "SALARY" in doc.header.privacy.entity_categories
        assert doc.header.graph.namespace == "hr.compensation"
        assert len(doc.sentences) > 0
        assert "John Smith" in doc.body

    def test_parse_finance_document(self):
        """Parse a finance document with RESTRICTED classification."""
        doc = self.parser.parse(FIXTURES_DIR / "sample_finance_doc.md")

        assert doc.header.document.id == "FIN-2026-00089"
        assert doc.header.document.classification == Classification.RESTRICTED

    def test_parse_text_directly(self):
        """Parse OKF content from a string."""
        content = """---
okf_version: "1.0"
document:
  id: "TEST-001"
  title: "Test Doc"
  classification: "PUBLIC"
  department: "Test"
  author: "test@test.com"
  created: "2026-01-01"
privacy:
  entity_categories: [PERSON]
  redaction_policy: "TOKENIZE"
  min_confidence: 0.9
graph:
  namespace: "test.ns"
---

This is a test sentence.
Another sentence here.
"""
        doc = self.parser.parse_text(content)

        assert doc.header.document.id == "TEST-001"
        assert doc.header.document.classification == Classification.PUBLIC
        assert len(doc.sentences) == 2

    def test_missing_frontmatter_raises_error(self):
        """Raise ValueError when frontmatter is missing."""
        with pytest.raises(ValueError, match="No OKF frontmatter"):
            self.parser.parse_text("Just plain text without headers.")

    def test_invalid_yaml_raises_error(self):
        """Raise ValueError when YAML is malformed."""
        content = """---
invalid: [yaml: {{
---

Body text.
"""
        with pytest.raises(ValueError, match="Invalid OKF header"):
            self.parser.parse_text(content)
