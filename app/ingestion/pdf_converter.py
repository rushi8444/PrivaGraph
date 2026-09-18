"""PDF to OKF (Open Knowledge Format) converter.

Extracts text and metadata from PDF files using PyMuPDF and synthesizes
a validated OKFDocument with standard security, privacy, and graph configurations.
"""

from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
import re
from typing import BinaryIO

import pymupdf
import yaml

from app.models.document import (
    AccessControl,
    Classification,
    DocumentMeta,
    GraphConfig,
    LinkStrategy,
    OKFDocument,
    OKFHeader,
    PrivacyConfig,
    RedactionPolicy,
)
from app.ingestion.table_parser import TableParser


class PDFToOKFConverter:
    """Converts PDF files into validated OKFDocument structures."""

    DEFAULT_ENTITY_CATEGORIES = [
        "PERSON",
        "EMAIL",
        "PHONE",
        "SSN",
        "SALARY",
        "LOCATION",
        "ORGANIZATION",
        "CREDIT_CARD",
    ]

    def __init__(self):
        self.table_parser = TableParser()

    def convert_file(
        self,
        file_path: Path | str,
        *,
        title: str | None = None,
        classification: Classification | str | None = None,
        department: str | None = None,
        author: str | None = None,
        allowed_roles: list[str] | None = None,
        entity_categories: list[str] | None = None,
    ) -> OKFDocument:
        """Convert a PDF file on disk to an OKFDocument."""
        path = Path(file_path)
        content = path.read_bytes()
        return self.convert(
            content=content,
            filename=path.name,
            title=title,
            classification=classification,
            department=department,
            author=author,
            allowed_roles=allowed_roles,
            entity_categories=entity_categories,
        )

    def convert(
        self,
        content: bytes | BinaryIO,
        filename: str = "document.pdf",
        *,
        title: str | None = None,
        classification: Classification | str | None = None,
        department: str | None = None,
        author: str | None = None,
        allowed_roles: list[str] | None = None,
        entity_categories: list[str] | None = None,
    ) -> OKFDocument:
        """Convert in-memory PDF binary content to an OKFDocument.

        Args:
            content: Raw PDF bytes or byte stream.
            filename: Source filename for metadata naming.
            title: Optional title override.
            classification: Optional Classification override.
            department: Optional department override.
            author: Optional author override.
            allowed_roles: Optional allowed roles override for RBAC.
            entity_categories: Optional entity categories for privacy scanning.

        Returns:
            Validated OKFDocument.

        Raises:
            ValueError: If PDF is invalid, empty, or contains no extractable text.
        """
        raw_bytes = content if isinstance(content, bytes) else content.read()
        if not raw_bytes:
            raise ValueError(f"Empty PDF file: '{filename}'")

        try:
            pdf_doc = pymupdf.open(stream=raw_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Failed to parse PDF '{filename}': {e}") from e

        # Extract tables and non-table text page by page
        page_non_table_texts: list[str] = []
        table_sentences: list[str] = []

        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            page_text = page.get_text("text")

            # Detect department roster heading on this page
            page_dept = None
            roster_match = re.search(
                r"\b(?:\d+[a-z]?\.?\s+)?([A-Za-z\s&]+?)\s+Department\s+Roster\b",
                page_text,
                re.IGNORECASE,
            )
            if roster_match:
                dept_raw = roster_match.group(1).strip().lower()
                if "engineering" in dept_raw:
                    page_dept = "Engineering"
                elif "sales" in dept_raw:
                    page_dept = "Sales"
                elif "operations" in dept_raw:
                    page_dept = "Operations"
                elif "marketing" in dept_raw:
                    page_dept = "Marketing"
                elif "customer success" in dept_raw:
                    page_dept = "Customer Success"
                elif "legal" in dept_raw:
                    page_dept = "Legal"
                elif "finance" in dept_raw:
                    page_dept = "Finance"
                elif "executive" in dept_raw:
                    page_dept = "Executive"
                else:
                    page_dept = roster_match.group(1).strip()

            table_bboxes = []
            try:
                tabs = page.find_tables()
                for tab in tabs:
                    table_bboxes.append(pymupdf.Rect(tab.bbox))
                    data = tab.extract()
                    if data and len(data) >= 2:
                        pipe_rows = [
                            " | ".join(str(c or "").strip().replace("\n", " ") for c in row)
                            for row in data
                        ]
                        parsed = self.table_parser._parse_pipe_table(pipe_rows)
                        if parsed:
                            table_sentences.extend(
                                self.table_parser.table_to_row_sentences(parsed, department=page_dept)
                            )
            except Exception:
                pass

            if table_bboxes:
                # Extract text blocks outside table boundaries
                blocks = page.get_text("blocks")
                for b in blocks:
                    if b[6] != 0:
                        continue
                    block_rect = pymupdf.Rect(b[:4])
                    if not any(block_rect.intersects(t_bbox) for t_bbox in table_bboxes):
                        text = b[4].strip()
                        if text:
                            page_non_table_texts.append(text)
            else:
                text = page.get_text("text")
                if text and text.strip():
                    page_non_table_texts.append(text.strip())

        full_body = "\n\n".join(page_non_table_texts).strip()
        if not full_body and not table_sentences:
            raise ValueError(
                f"No extractable text found in '{filename}'. "
                "The PDF may be an image-only scan or empty. OCR is not currently supported."
            )

        # Extract metadata from PDF or infer defaults
        pdf_meta = pdf_doc.metadata or {}

        # 1. Document ID
        clean_stem = re.sub(r"[^\w\-_]", "", Path(filename).stem) or "doc"
        content_hash = hashlib.sha256(raw_bytes[:1024]).hexdigest()[:6]
        doc_id = f"PDF-{clean_stem[:24]}-{content_hash}".upper()

        # 2. Title
        title_str = title if isinstance(title, str) and title.strip() else None
        resolved_title = title_str or pdf_meta.get("title")
        if not resolved_title or not str(resolved_title).strip() or str(resolved_title).strip() == "(anonymous)":
            # Try to grab the first non-empty line of text if it looks like a heading
            first_line = full_body.splitlines()[0].strip() if full_body else ""
            if first_line and len(first_line) < 100:
                resolved_title = first_line
            else:
                resolved_title = Path(filename).stem.replace("_", " ").replace("-", " ").title()

        # 3. Author
        author_str = author if isinstance(author, str) and author.strip() else None
        resolved_author = author_str or pdf_meta.get("author") or "System Ingest"
        if not str(resolved_author).strip() or str(resolved_author).strip() == "(anonymous)":
            resolved_author = "System Ingest"

        # 4. Created date
        created_date = self._parse_pdf_date(pdf_meta.get("creationDate"))

        # 5. Classification
        if isinstance(classification, str):
            try:
                resolved_classification = Classification(classification.upper())
            except ValueError:
                resolved_classification = Classification.INTERNAL
        elif isinstance(classification, Classification):
            resolved_classification = classification
        else:
            resolved_classification = Classification.INTERNAL

        # 6. Department
        dept_str = department if isinstance(department, str) and department.strip() else None
        resolved_dept = dept_str or "General"

        # 7. Roles & Access Control
        resolved_roles = (
            allowed_roles
            if allowed_roles is not None
            else ["admin", "employee", "hr_manager", "cfo", "compliance_officer"]
        )

        # 8. Privacy scanning categories
        resolved_categories = (
            entity_categories
            if entity_categories is not None
            else self.DEFAULT_ENTITY_CATEGORIES
        )

        # 9. Graph namespace
        slug = re.sub(r"[^a-zA-Z0-9_]", "_", clean_stem).lower()
        namespace = f"pdf.{slug}"

        # Build OKF Header
        header = OKFHeader(
            okf_version="1.0",
            document=DocumentMeta(
                id=doc_id,
                title=resolved_title,
                classification=resolved_classification,
                department=resolved_dept,
                author=resolved_author,
                created=created_date,
            ),
            privacy=PrivacyConfig(
                entity_categories=resolved_categories,
                redaction_policy=RedactionPolicy.TOKENIZE,
                min_confidence=0.85,
            ),
            access_control=AccessControl(
                allowed_roles=resolved_roles,
                denied_roles=[],
            ),
            graph=GraphConfig(
                namespace=namespace,
                link_strategy=LinkStrategy.CROSS_DOCUMENT,
                max_traversal_depth=3,
            ),
        )

        sentences = self._split_sentences(full_body, extra_sentences=table_sentences)

        return OKFDocument(
            source_path=filename,
            header=header,
            body=full_body,
            sentences=sentences,
        )

    def to_okf_markdown(self, doc: OKFDocument) -> str:
        """Serialize an OKFDocument into standard OKF Markdown with YAML frontmatter."""
        header_dict = doc.header.model_dump(mode="json")
        yaml_frontmatter = yaml.dump(header_dict, sort_keys=False)
        return f"---\n{yaml_frontmatter}---\n\n# {doc.header.document.title}\n\n{doc.body}\n"

    def _parse_pdf_date(self, raw_date: str | None) -> date:
        """Parse PDF date format 'D:YYYYMMDD...' into a standard date object."""
        if not raw_date:
            return date.today()

        match = re.search(r"(\d{4})(\d{2})(\d{2})", raw_date)
        if match:
            try:
                year, month, day = map(int, match.groups())
                return date(year, month, day)
            except ValueError:
                pass

        return date.today()

    def _split_sentences(self, text: str, extra_sentences: list[str] | None = None) -> list[str]:
        """Split extracted PDF text into clean, individual sentences.

        Extracts tables first into row-scoped sentences to prevent cross-row cartesian explosion.
        """
        # 1. Extract tables and convert them to row-scoped sentences
        text_without_tables, table_sentences = self.table_parser.convert_tables_in_text(text)

        sentences: list[str] = []
        blocks = re.split(r"\n\s*\n+", text_without_tables)

        for block in blocks:
            # Flatten soft line breaks within paragraphs into single spaces
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            block_clean = " ".join(lines)
            if not block_clean:
                continue

            # Split on sentence terminals followed by whitespace
            raw_sents = re.split(r"(?<=[.!?])\s+", block_clean)
            for s in raw_sents:
                clean_s = s.strip()
                if clean_s:
                    sentences.append(clean_s)

        # 2. Append table-generated row sentences
        sentences.extend(table_sentences)
        if extra_sentences:
            sentences.extend(extra_sentences)
        return sentences
