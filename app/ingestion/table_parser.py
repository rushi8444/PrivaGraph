"""Table parser for row-scoped entity and relation extraction.

Detects Markdown and structured text tables, isolates each row,
and converts rows into strictly row-scoped sentences to prevent
cartesian graph cross-contamination.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass
class TableRow:
    """A single row in a parsed table."""

    subject: str
    properties: dict[str, str]  # normalized_predicate -> cell_value


@dataclass
class ParsedTable:
    """A structured table extracted from text."""

    headers: list[str]
    rows: list[TableRow]
    raw_text: str


HEADER_PREDICATE_MAP: dict[str, str] = {
    "ssn": "HAS_SSN",
    "social security": "HAS_SSN",
    "social security number": "HAS_SSN",
    "salary": "HAS_SALARY",
    "compensation": "HAS_SALARY",
    "pay": "HAS_SALARY",
    "wage": "HAS_SALARY",
    "annual salary": "HAS_SALARY",
    "base salary": "HAS_SALARY",
    "email": "HAS_EMAIL",
    "email address": "HAS_EMAIL",
    "phone": "HAS_PHONE",
    "phone number": "HAS_PHONE",
    "mobile": "HAS_PHONE",
    "contact": "HAS_CONTACT",
    "role": "HAS_ROLE",
    "title": "HAS_ROLE",
    "job title": "HAS_ROLE",
    "position": "HAS_ROLE",
    "department": "IN_DEPARTMENT",
    "dept": "IN_DEPARTMENT",
    "manager": "REPORTS_TO",
    "reports to": "REPORTS_TO",
    "supervisor": "REPORTS_TO",
    "reason": "HAS_REASON",
    "status": "HAS_STATUS",
    "address": "HAS_ADDRESS",
    "home address": "HAS_ADDRESS",
    "street address": "HAS_ADDRESS",
    "location": "LOCATED_IN",
    "hire date": "HIRED_ON",
    "start date": "STARTED_ON",
}



def normalize_header_to_predicate(header: str) -> str:
    """Map a table column header to a canonical graph predicate."""
    clean = header.strip().lower()
    if clean in HEADER_PREDICATE_MAP:
        return HEADER_PREDICATE_MAP[clean]

    # Remove non-alphanumeric chars
    slug = re.sub(r"[^\w\s]", "", clean).strip()
    slug = re.sub(r"\s+", "_", slug).upper()
    return f"HAS_{slug}" if slug else "RELATED_TO"


class TableParser:
    """Detects and parses Markdown and delimited text tables into row-scoped structures."""

    # Matches Markdown table separators like |---|:---|---:|
    MD_SEPARATOR_PATTERN = re.compile(r"^\s*\|?\s*(?::?-+:?\s*\|)+\s*(?::?-+:?\s*)?\|?\s*$")

    def parse_markdown_tables(self, text: str) -> list[ParsedTable]:
        """Extract Markdown tables with '|' delimiters."""
        tables: list[ParsedTable] = []
        lines = text.splitlines()
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i].strip()
            # Check if this line looks like a table header followed by a separator line
            if "|" in line and i + 1 < n and self.MD_SEPARATOR_PATTERN.match(lines[i + 1].strip()):
                table_lines = [lines[i], lines[i + 1]]
                i += 2
                while i < n and "|" in lines[i]:
                    table_lines.append(lines[i])
                    i += 1

                parsed = self._parse_pipe_table(table_lines)
                if parsed and parsed.rows:
                    tables.append(parsed)
            elif "|" in line and not line.startswith("#"):
                # Check for pipe-separated table without markdown separator row
                # Requires at least 2 consecutive lines with the same number of pipe columns
                potential_rows = [line]
                j = i + 1
                while j < n and "|" in lines[j] and not lines[j].strip().startswith("#"):
                    potential_rows.append(lines[j].strip())
                    j += 1
                if len(potential_rows) >= 2:
                    parsed = self._parse_pipe_table(potential_rows)
                    if parsed and parsed.rows:
                        tables.append(parsed)
                        i = j
                        continue
                i += 1
            else:
                i += 1

        return tables

    def _parse_pipe_table(self, lines: list[str]) -> ParsedTable | None:
        """Parse pipe-delimited table lines into a ParsedTable."""
        clean_rows: list[list[str]] = []
        for line in lines:
            line_str = line.strip()
            # Strip leading/trailing pipes
            if line_str.startswith("|"):
                line_str = line_str[1:]
            if line_str.endswith("|"):
                line_str = line_str[:-1]
            cells = [c.strip() for c in line_str.split("|")]
            # Skip separator row e.g. | --- | --- |
            if all(re.match(r"^:?-+:?$", c) for c in cells if c):
                continue
            if any(cells):
                clean_rows.append(cells)

        if len(clean_rows) < 2:
            return None

        headers = clean_rows[0]
        data_rows = clean_rows[1:]

        # Normalize headers
        predicates = [normalize_header_to_predicate(h) for h in headers]

        table_rows: list[TableRow] = []
        for row in data_rows:
            if not row or not any(row):
                continue
            subject = row[0]
            if not subject:
                continue

            properties: dict[str, str] = {}
            for col_idx in range(1, min(len(row), len(predicates))):
                val = row[col_idx].strip()
                if val:
                    pred = predicates[col_idx]
                    properties[pred] = val

            if properties:
                table_rows.append(TableRow(subject=subject, properties=properties))

        return ParsedTable(
            headers=headers,
            rows=table_rows,
            raw_text="\n".join(lines),
        )

    def table_to_row_sentences(
        self,
        table: ParsedTable,
        department: str | None = None,
    ) -> list[str]:
        """Convert a ParsedTable into strictly row-scoped sentences.

        Each sentence explicitly binds the row subject to exactly ONE property,
        guaranteeing zero cross-row entanglement.
        """
        sentences: list[str] = []
        for row in table.rows:
            subj = row.subject
            # If a section/department context is known, explicitly bind subject to department
            if department and "IN_DEPARTMENT" not in row.properties:
                sentences.append(f"{subj} works in {department} department.")

            for pred, val in row.properties.items():
                # Format friendly sentence that NER and TripleExtractor can unambiguously parse
                if pred == "HAS_SSN":
                    sentences.append(f"{subj} has SSN {val}.")
                elif pred == "HAS_SALARY":
                    sentences.append(f"{subj} earns {val}.")
                elif pred == "HAS_EMAIL":
                    sentences.append(f"{subj} has email {val}.")
                elif pred == "HAS_PHONE":
                    sentences.append(f"{subj} has contact {val}.")
                elif pred == "HAS_ROLE":
                    sentences.append(f"{subj} is a {val}.")
                elif pred == "IN_DEPARTMENT":
                    sentences.append(f"{subj} works in {val} department.")
                elif pred == "REPORTS_TO":
                    sentences.append(f"{subj} reports to {val}.")
                elif pred == "HAS_REASON":
                    sentences.append(f"{subj} has reason {val}.")
                elif pred == "HAS_ADDRESS":
                    sentences.append(f"{subj} has address {val}.")
                elif pred == "HIRED_ON":
                    sentences.append(f"{subj} was hired on {val}.")
                else:
                    attr_name = pred.removeprefix("HAS_").replace("_", " ").lower()
                    sentences.append(f"{subj} has {attr_name} {val}.")

        return sentences

    def convert_tables_in_text(self, text: str) -> tuple[str, list[str]]:
        """Find tables in text, remove their raw block, and return table-generated row sentences."""
        tables = self.parse_markdown_tables(text)
        if not tables:
            return text, []

        modified_text = text
        table_sentences: list[str] = []

        for table in tables:
            row_sents = self.table_to_row_sentences(table)
            table_sentences.extend(row_sents)
            # Replace raw table text with a placeholder newline so it doesn't get concatenated as a paragraph
            modified_text = modified_text.replace(table.raw_text, "\n")

        return modified_text, table_sentences
