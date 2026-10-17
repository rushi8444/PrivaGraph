"""Shared heuristics for recognising organization (company) names."""

from __future__ import annotations

import re

ORG_SUFFIX_WORDS = (
    "Inc", "LLC", "Ltd", "Limited", "Pvt", "Corp", "Corporation", "Co", "LLP", "GmbH",
    "Technologies", "Technology", "Tech", "Solutions", "Labs", "Systems", "Infotech",
    "Software", "Softwares", "Services", "Group", "Consulting", "Enterprises",
    "Industries", "Studio", "Studios", "Infosystems", "Networks", "Digital",
)

_SUFFIX_ALT = "|".join(ORG_SUFFIX_WORDS)

# Used to classify an already-isolated value ("Devsync IT Solutions").
ORG_VALUE_RE = re.compile(rf"\b(?:{_SUFFIX_ALT})\b\.?$", re.IGNORECASE)
# Used to find organizations inside free text (capitalized words ending in a suffix).
ORG_TEXT_PATTERN = rf"\b(?:[A-Z][\w&.-]*\s+){{0,4}}(?:{_SUFFIX_ALT})\b\.?"
# Detects an org suffix word anywhere inside a candidate span.
ORG_ANYWHERE_RE = re.compile(rf"\b(?:{_SUFFIX_ALT})\b", re.IGNORECASE)


def looks_like_organization(value: str) -> bool:
    """True if the value ends in a typical company suffix (Inc, Solutions, Labs...)."""
    return bool(ORG_VALUE_RE.search(value.strip()))


def contains_org_word(value: str) -> bool:
    return bool(ORG_ANYWHERE_RE.search(value))
