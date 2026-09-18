"""OKF (Open Knowledge Format) document parser.

Parses Markdown files with custom YAML frontmatter headers that declare
security metadata, privacy scanning rules, RBAC policies, and graph config.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.ingestion.table_parser import TableParser
from app.models.document import OKFDocument, OKFHeader


class OKFParser:
    """Parses Markdown files with OKF YAML frontmatter headers."""

    FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n(.*)",
        re.DOTALL,
    )

    def __init__(self):
        self.table_parser = TableParser()

    def parse(self, file_path: Path) -> OKFDocument:
        """Parse an OKF Markdown file into a validated document model.

        Args:
            file_path: Path to the Markdown file with OKF frontmatter.

        Returns:
            Validated OKFDocument with parsed header and body.

        Raises:
            ValueError: If frontmatter is missing or invalid.
        """
        content = file_path.read_text(encoding="utf-8")
        return self.parse_text(content, source_path=str(file_path))

    def parse_text(self, content: str, source_path: str = "<string>") -> OKFDocument:
        """Parse OKF content from a string.

        Args:
            content: Full document text including YAML frontmatter.
            source_path: Source identifier for error messages.

        Returns:
            Validated OKFDocument.
        """
        match = self.FRONTMATTER_PATTERN.match(content)

        if not match:
            raise ValueError(f"No OKF frontmatter found in {source_path}")

        raw_yaml, body = match.group(1), match.group(2)

        try:
            header_data = yaml.safe_load(raw_yaml)
            header = OKFHeader(**header_data)
        except (yaml.YAMLError, ValidationError) as e:
            raise ValueError(f"Invalid OKF header in {source_path}: {e}") from e

        return OKFDocument(
            source_path=source_path,
            header=header,
            body=body.strip(),
            sentences=self._split_sentences(body.strip()),
        )

    def _split_sentences(self, text: str) -> list[str]:
        """Split body text into clean sentences for per-sentence NER and triple extraction.

        Extracts tables first into row-scoped sentences to prevent cross-row cartesian explosion.
        Strips markdown headings and splits paragraphs by sentence boundaries.
        """
        # 1. Extract tables and convert them to row-scoped sentences
        text_without_tables, table_sentences = self.table_parser.convert_tables_in_text(text)

        sentences: list[str] = []
        blocks = re.split(r"\n\s*\n+", text_without_tables)
        for block in blocks:
            # Strip pure markdown headers (e.g. '# Header') from sentence content
            lines = [
                re.sub(r"^#+\s*", "", line).strip()
                for line in block.splitlines()
                if line.strip()
            ]
            block_clean = " ".join(lines)
            if not block_clean:
                continue

            raw_sents = re.split(r"(?<=[.!?])\s+", block_clean)
            for s in raw_sents:
                clean_s = s.strip()
                # Skip if the sentence is just a short heading or empty
                if clean_s:
                    sentences.append(clean_s)

        # 2. Append table-generated row sentences
        sentences.extend(table_sentences)
        return sentences
