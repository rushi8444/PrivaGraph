"""Common table constants and normalization utilities.

Extracted to break circular import dependencies between table_parser and composite_unpacker.
"""

from __future__ import annotations

import re

# Marker: a column of plain, non-sensitive attributes (never tokenized or relabelled by NER).
PLAIN = "PLAIN"

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
