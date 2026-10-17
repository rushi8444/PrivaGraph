"""Table parser for row-scoped entity and relation extraction.

Detects Markdown and structured text tables, isolates each row,
and converts rows into strictly row-scoped sentences to prevent
cartesian graph cross-contamination.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from app.detection.org_patterns import looks_like_organization
from app.ingestion.composite_unpacker import CompositeCellDecomposer
from app.models.document import TypedSpan

from app.ingestion.table_common import (
    PLAIN,
    HEADER_PREDICATE_MAP,
    normalize_header_to_predicate,
)

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
    # Populated only when type inference is requested (CSV/XLSX).
    # Values are entity types, PLAIN, or None (= unknown, let NER decide).
    subject_type: str | None = None
    predicate_types: dict[str, str | None] = field(default_factory=dict)



# Predicates whose cell values have a known sensitive entity type.
PREDICATE_ENTITY_TYPE: dict[str, str] = {
    "HAS_SSN": "US_SSN",
    "HAS_SALARY": "SALARY",
    "HAS_EMAIL": "EMAIL_ADDRESS",
    "HAS_PHONE": "PHONE_NUMBER",
    "HAS_ADDRESS": "LOCATION",
    "LOCATED_IN": "LOCATION",
    "REPORTS_TO": "PERSON",
}

_ORG_HEADER_RE = re.compile(
    r"\b(company|companies|organi[sz]ation|firm|employer|vendor|client|business|agency|supplier)\b"
)
_PERSON_HEADER_RE = re.compile(
    r"^(name|full name|person|employee|employee name|contact person|candidate|student)$"
)
_URL_HEADER_RE = re.compile(r"\b(website|url|link|maps|web)\b")
_RATING_HEADER_RE = re.compile(r"\b(rating|ratings|score|stars?|reviews?)\b")
_CATEGORY_HEADER_RE = re.compile(
    r"\b(category|categories|industry|type|sector|service|services|status|domain)\b"
)
_URL_VALUE_RE = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)
_RATING_VALUE_RE = re.compile(r"^\d(\.\d)?\s*(\(\d+\))?$")
_PERSON_VALUE_RE = re.compile(r"^[A-Za-z.'\-]+(?:\s+[A-Za-z.'\-]+){1,3}$")


def _fraction(values: list[str], pattern: re.Pattern[str]) -> float:
    return sum(1 for v in values if pattern.search(v)) / len(values) if values else 0.0


def infer_column_type(header: str, values: list[str]) -> str | None:
    """Infer the entity type of a column from its header, then its values.

    Returns an entity type (e.g. ORGANIZATION), PLAIN for non-sensitive
    attributes (URL, rating, category), or None when unknown (NER decides).
    """
    h = header.strip().lower()
    predicate = normalize_header_to_predicate(header)
    if predicate in PREDICATE_ENTITY_TYPE:
        return PREDICATE_ENTITY_TYPE[predicate]

    vals = [v.strip() for v in values if v and v.strip()]
    if not vals:
        return None

    if _ORG_HEADER_RE.search(h):
        return "ORGANIZATION"
    if _URL_HEADER_RE.search(h) or _fraction(vals, _URL_VALUE_RE) >= 0.8:
        return PLAIN
    if _RATING_HEADER_RE.search(h) or _fraction(vals, _RATING_VALUE_RE) >= 0.8:
        return PLAIN
    if sum(1 for v in vals if looks_like_organization(v)) / len(vals) >= 0.5:
        return "ORGANIZATION"
    if _PERSON_HEADER_RE.match(h) and _fraction(vals, _PERSON_VALUE_RE) >= 0.5:
        return "PERSON"
    if _CATEGORY_HEADER_RE.search(h):
        return PLAIN
    return None


class TableParser:
    """Detects and parses Markdown and delimited text tables into row-scoped structures."""

    # Matches Markdown table separators like |---|:---|---:|
    MD_SEPARATOR_PATTERN = re.compile(r"^\s*\|?\s*(?::?-+:?\s*\|)+\s*(?::?-+:?\s*)?\|?\s*$")

    def __init__(self):
        self.decomposer = CompositeCellDecomposer()

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

        return self.parse_cell_rows(clean_rows, raw_text="\n".join(lines))

    def parse_cell_rows(
        self,
        clean_rows: list[list[str]],
        raw_text: str = "",
        infer_types: bool = False,
    ) -> ParsedTable | None:
        """Build a ParsedTable from already-split rows (first row = headers)."""
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

        subject_type: str | None = None
        predicate_types: dict[str, str | None] = {}
        if infer_types:
            sample = data_rows[:50]
            for idx, header in enumerate(headers):
                col_vals = [r[idx] for r in sample if idx < len(r)]
                col_type = infer_column_type(header, col_vals)
                if idx == 0:
                    subject_type = col_type
                else:
                    predicate_types[predicates[idx]] = col_type

        return ParsedTable(
            headers=headers,
            rows=table_rows,
            raw_text=raw_text,
            subject_type=subject_type,
            predicate_types=predicate_types,
        )

    _TEMPLATES: dict[str, str] = {
        "HAS_SSN": "{subj} has SSN {val}.",
        "HAS_SALARY": "{subj} earns {val}.",
        "HAS_EMAIL": "{subj} has email {val}.",
        "HAS_PHONE": "{subj} has contact {val}.",
        "HAS_HOURS": "{subj} has operating hours {val}.",
        "HAS_ROLE": "{subj} is a {val}.",
        "HAS_CATEGORY": "{subj} is a {val}.",
        "IN_DEPARTMENT": "{subj} works in {val} department.",
        "REPORTS_TO": "{subj} reports to {val}.",
        "HAS_REASON": "{subj} has reason {val}.",
        "HAS_ADDRESS": "{subj} has address {val}.",
        "HIRED_ON": "{subj} was hired on {val}.",
        "HAS_RATING": "{subj} has rating {val}.",
        "HAS_LINK": "{subj} has google maps link {val}.",
        "HAS_WEBSITE": "{subj} has website {val}.",
    }

    def table_to_row_sentences(
        self,
        table: ParsedTable,
        department: str | None = None,
    ) -> list[str]:
        """Convert a ParsedTable into strictly row-scoped sentences.

        Each sentence explicitly binds the row subject to exactly ONE property,
        guaranteeing zero cross-row entanglement.
        """
        sentences, _ = self.table_to_typed_sentences(table, department)
        return sentences

    def table_to_typed_sentences(
        self,
        table: ParsedTable,
        department: str | None = None,
    ) -> tuple[list[str], list[list[TypedSpan]]]:
        """Like table_to_row_sentences, but also returns per-sentence typed spans.

        Spans are only produced for columns whose type was inferred
        (see parse_cell_rows(infer_types=True)); otherwise every span list is empty.
        """
        sentences: list[str] = []
        hints: list[list[TypedSpan]] = []
        for row in table.rows:
            subj = row.subject
            # If a section/department context is known, explicitly bind subject to department
            if department and "IN_DEPARTMENT" not in row.properties:
                sentence = f"{subj} works in {department} department."
                sentences.append(sentence)
                hints.append(self._subject_hint(table, subj))

            for pred, val in row.properties.items():
                if self.decomposer.is_composite(val):
                    facts = self.decomposer.decompose(val, subject_name=subj)
                    if facts:
                        for fact in facts:
                            sub_pred = fact.predicate
                            sub_val = fact.value
                            template = self._TEMPLATES.get(sub_pred)
                            if template is None:
                                attr_name = sub_pred.removeprefix("HAS_").replace("_", " ").lower()
                                template = "{subj} has " + attr_name + " {val}."
                            sentence = template.format(subj=subj, val=sub_val)
                            sentences.append(sentence)

                            spans = self._subject_hint(table, subj)
                            if fact.entity_type is not None:
                                idx = sentence.rfind(sub_val)
                                if idx >= len(subj):
                                    spans.append(
                                        TypedSpan(
                                            start=idx,
                                            end=idx + len(sub_val),
                                            entity_type=fact.entity_type,
                                        )
                                    )
                            hints.append(spans)
                        continue

                # Format friendly sentence that NER and TripleExtractor can unambiguously parse
                template = self._TEMPLATES.get(pred)
                if template is None:
                    attr_name = pred.removeprefix("HAS_").replace("_", " ").lower()
                    template = "{subj} has " + attr_name + " {val}."
                sentence = template.format(subj=subj, val=val)
                sentences.append(sentence)

                spans = self._subject_hint(table, subj)
                if pred in table.predicate_types:
                    col_type = table.predicate_types[pred]
                    idx = sentence.rfind(val)
                    if col_type is not None and idx >= len(subj):
                        spans.append(
                            TypedSpan(
                                start=idx,
                                end=idx + len(val),
                                entity_type=None if col_type == PLAIN else col_type,
                            )
                        )
                hints.append(spans)

        return sentences, hints

    @staticmethod
    def _subject_hint(table: ParsedTable, subj: str) -> list[TypedSpan]:
        if table.subject_type is None:
            return []
        return [
            TypedSpan(
                start=0,
                end=len(subj),
                entity_type=None if table.subject_type == PLAIN else table.subject_type,
            )
        ]

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
