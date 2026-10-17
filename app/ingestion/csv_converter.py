"""CSV to OKF (Open Knowledge Format) converter.

Parses CSV content, treats the first row as headers and the first column as
the row subject, and converts each row into row-scoped sentences using the
shared TableParser. The result is a validated OKFDocument.
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import date
from pathlib import Path
import re

from app.ingestion.pdf_converter import PDFToOKFConverter
from app.ingestion.table_parser import TableParser
from app.models.document import (
    Classification,
    DocumentMeta,
    GraphConfig,
    LinkStrategy,
    OKFDocument,
    OKFHeader,
    PrivacyConfig,
    RedactionPolicy,
)


class CSVToOKFConverter:
    """Converts CSV files into validated OKFDocument structures."""

    def __init__(self):
        self.table_parser = TableParser()

    @staticmethod
    def _read_xlsx_sheets(content: bytes, filename: str) -> list[tuple[str, list[list[str]]]]:
        """Read all non-empty sheets of an .xlsx workbook as (sheet_title, rows) tuples."""
        try:
            from openpyxl import load_workbook
        except ImportError as e:  # pragma: no cover
            raise ValueError("Excel support requires 'openpyxl' (pip install openpyxl).") from e

        try:
            wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception as e:
            raise ValueError(f"'{filename}' is not a readable .xlsx workbook: {e}") from e

        sheets_data = []
        try:
            for ws in wb.worksheets:
                rows = [
                    ["" if c is None else str(c).strip() for c in row]
                    for row in ws.iter_rows(values_only=True)
                ]
                rows = [r for r in rows if any(r)]
                if rows:
                    sheets_data.append((ws.title or "Sheet", rows))
        finally:
            wb.close()
        return sheets_data

    @classmethod
    def _read_xlsx_rows(cls, content: bytes, filename: str) -> list[list[str]]:
        """Backwards-compatible helper: read first non-empty sheet."""
        sheets = cls._read_xlsx_sheets(content, filename)
        return sheets[0][1] if sheets else []

    def convert(
        self,
        content: bytes,
        filename: str = "document.csv",
        *,
        title: str | None = None,
        classification: Classification | str | None = None,
        department: str | None = None,
        author: str | None = None,
        entity_categories: list[str] | None = None,
    ) -> OKFDocument:
        """Convert raw CSV or Excel .xlsx bytes to an OKFDocument.

        Raises:
            ValueError: If the file is empty, undecodable, or has no data rows.
        """
        if not content:
            raise ValueError(f"Empty document file: '{filename}'")

        # Legacy binary .xls is an OLE2 container.
        if content.startswith(b"\xd0\xcf\x11\xe0"):
            raise ValueError(
                f"'{filename}' is a legacy .xls workbook, which is not supported. "
                "Open it in Excel and use File > Save As > '.xlsx' (or CSV UTF-8), then upload again."
            )

        is_xlsx = content.startswith(b"PK\x03\x04") or Path(filename).suffix.lower() in (".xlsx", ".xlsm")

        all_sentences: list[str] = []
        all_hints: list[dict] = []

        if is_xlsx:
            sheets_data = self._read_xlsx_sheets(content, filename)
            if not sheets_data:
                raise ValueError(
                    f"No usable data rows in '{filename}'. "
                    "Excel workbook has no non-empty sheets."
                )
            for sheet_name, rows in sheets_data:
                table = self.table_parser.parse_cell_rows(rows, infer_types=True)
                if table and table.rows:
                    sents, hints = self.table_parser.table_to_typed_sentences(table)
                    all_sentences.extend(sents)
                    all_hints.extend(hints)
        else:
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = content.decode("latin-1")

            try:
                dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel

            rows = [
                [c.strip() for c in row]
                for row in csv.reader(io.StringIO(text), dialect)
                if any(c.strip() for c in row)
            ]
            table = self.table_parser.parse_cell_rows(rows, infer_types=True)
            if table and table.rows:
                sents, hints = self.table_parser.table_to_typed_sentences(table)
                all_sentences.extend(sents)
                all_hints.extend(hints)

        if not all_sentences:
            raise ValueError(
                f"No usable data rows in '{filename}'. "
                "File needs a header row and at least one row with data."
            )

        resolved_dept = department if isinstance(department, str) and department.strip() else "General"
        sentences = all_sentences
        sentence_hints = all_hints
        body = "\n".join(sentences)

        clean_stem = re.sub(r"[^\w\-_]", "", Path(filename).stem) or "doc"
        content_hash = hashlib.sha256(content[:1024]).hexdigest()[:6]
        prefix = "XLSX" if is_xlsx else "CSV"
        doc_id = f"{prefix}-{clean_stem[:24]}-{content_hash}".upper()

        resolved_title = (
            title if isinstance(title, str) and title.strip()
            else Path(filename).stem.replace("_", " ").replace("-", " ").title()
        )
        resolved_author = author if isinstance(author, str) and author.strip() else "System Ingest"

        if isinstance(classification, Classification):
            resolved_class = classification
        elif isinstance(classification, str):
            try:
                resolved_class = Classification(classification.upper())
            except ValueError:
                resolved_class = Classification.INTERNAL
        else:
            resolved_class = Classification.INTERNAL

        slug = re.sub(r"[^a-zA-Z0-9_]", "_", clean_stem).lower()
        ns_prefix = "xlsx" if is_xlsx else "csv"

        header = OKFHeader(
            okf_version="1.0",
            document=DocumentMeta(
                id=doc_id,
                title=resolved_title,
                classification=resolved_class,
                department=resolved_dept,
                author=resolved_author,
                created=date.today(),
            ),
            privacy=PrivacyConfig(
                entity_categories=entity_categories or PDFToOKFConverter.DEFAULT_ENTITY_CATEGORIES,
                redaction_policy=RedactionPolicy.TOKENIZE,
                min_confidence=0.85,
            ),
            graph=GraphConfig(
                namespace=f"{ns_prefix}.{slug}",
                link_strategy=LinkStrategy.CROSS_DOCUMENT,
                max_traversal_depth=3,
            ),
        )

        return OKFDocument(
            source_path=filename,
            header=header,
            body=body,
            sentences=sentences,
            sentence_hints=sentence_hints,
        )
