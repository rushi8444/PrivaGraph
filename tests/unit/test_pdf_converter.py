"""Unit tests for the PDF to OKF converter."""

from datetime import date
from pathlib import Path
import pytest
import pymupdf

from app.ingestion.pdf_converter import PDFToOKFConverter
from app.models.document import Classification, OKFDocument

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestPDFToOKFConverter:
    """Tests for PDFToOKFConverter."""

    def setup_method(self):
        self.converter = PDFToOKFConverter()

    def test_convert_valid_pdf_file(self):
        """Convert sample PDF fixture and verify metadata and sentence extraction."""
        pdf_path = FIXTURES_DIR / "sample_employee_record.pdf"
        doc = self.converter.convert_file(pdf_path)

        assert isinstance(doc, OKFDocument)
        assert doc.header.okf_version == "1.0"
        assert doc.header.document.title == "Engineering Department Payroll Summary"
        assert doc.header.document.author == "hr-department@acme.corp"
        assert doc.header.document.created == date(2026, 7, 15)
        assert doc.header.document.classification == Classification.INTERNAL
        assert doc.header.document.department == "General"

        # Check privacy scanning defaults
        assert "PERSON" in doc.header.privacy.entity_categories
        assert "SALARY" in doc.header.privacy.entity_categories
        assert "SSN" in doc.header.privacy.entity_categories

        # Check sentences
        assert len(doc.sentences) >= 3
        combined = " ".join(doc.sentences)
        assert "Alice Williams" in combined
        assert "987-65-4321" in combined
        assert "$210,000" in combined

    def test_convert_with_metadata_overrides(self):
        """Convert PDF with custom overrides."""
        pdf_path = FIXTURES_DIR / "sample_employee_record.pdf"
        doc = self.converter.convert_file(
            pdf_path,
            title="Executive Salary Review",
            classification="CONFIDENTIAL",
            department="Cloud Engineering",
            author="custom.auditor@acme.corp",
            allowed_roles=["cfo", "auditor"],
        )

        assert doc.header.document.title == "Executive Salary Review"
        assert doc.header.document.classification == Classification.CONFIDENTIAL
        assert doc.header.document.department == "Cloud Engineering"
        assert doc.header.document.author == "custom.auditor@acme.corp"
        assert doc.header.access_control.allowed_roles == ["cfo", "auditor"]

    def test_convert_raw_bytes(self):
        """Convert in-memory PDF bytes directly."""
        pdf_path = FIXTURES_DIR / "sample_employee_record.pdf"
        raw_bytes = pdf_path.read_bytes()
        doc = self.converter.convert(raw_bytes, filename="uploaded_payroll.pdf")

        assert doc.source_path == "uploaded_payroll.pdf"
        assert doc.header.document.id.startswith("PDF-UPLOADED_PAYROLL-")
        assert len(doc.sentences) > 0

    def test_to_okf_markdown_serialization(self):
        """Verify serializing synthesized OKFDocument to valid OKF Markdown with YAML frontmatter."""
        pdf_path = FIXTURES_DIR / "sample_employee_record.pdf"
        doc = self.converter.convert_file(pdf_path)
        markdown = self.converter.to_okf_markdown(doc)

        assert markdown.startswith("---\n")
        assert 'okf_version: "1.0"' in markdown or "okf_version: '1.0'" in markdown
        assert "Engineering Department Payroll Summary" in markdown
        assert "Alice Williams" in markdown

    def test_empty_bytes_raises_error(self):
        """Empty PDF payload raises ValueError."""
        with pytest.raises(ValueError, match="Empty PDF file"):
            self.converter.convert(b"", filename="empty.pdf")

    def test_corrupt_pdf_raises_error(self):
        """Invalid PDF data raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse PDF"):
            self.converter.convert(b"not a real pdf content", filename="corrupt.pdf")

    def test_pdf_without_text_raises_error(self):
        """PDF with no extractable text raises ValueError with clear OCR guidance."""
        # Create an empty page PDF with no text
        empty_doc = pymupdf.open()
        empty_doc.new_page()
        pdf_bytes = empty_doc.tobytes()
        empty_doc.close()

        with pytest.raises(ValueError, match="No extractable text found"):
            self.converter.convert(pdf_bytes, filename="scanned_blank.pdf")
