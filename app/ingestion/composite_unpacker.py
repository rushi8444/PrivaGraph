"""Generalized Composite Cell Decomposer for multi-attribute unstructured cells."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ingestion.table_common import normalize_header_to_predicate, PLAIN


@dataclass
class DecomposedFact:
    predicate: str
    value: str
    entity_type: str | None = None  # None for PLAIN


class CompositeCellDecomposer:
    """Decomposes multi-attribute composite text cells into discrete semantic facts.

    Works across arbitrary domains (HR notes, Google Maps details, CRM logs,
    vendor info, healthcare remarks) by combining:
      1. Explicit 'Key: Value' label extraction.
      2. Universal entity pattern matching (phones, emails, currencies, hours, addresses, ratings).
      3. UI artifact and duplicate subject noise filtering.
    """

    # Universal Entity Patterns
    EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    # Global phone formats: US/Intl standard, Indian mobile (0/91 6-9xxxxxxxx), Landlines
    PHONE_RE = re.compile(
        r"(?:\+?91[\s-]?)?0?[6-9]\d{4}[\s-]?\d{5}\b|"  # Indian mobile
        r"\b0\d{2,4}[\s-]?\d{6,8}\b|"                   # Landline / STD
        r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|"  # US/Intl standard
        r"\+\d{1,4}[\s-]?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}\b"  # Global E.164
    )

    HOURS_RE = re.compile(
        r"(?:[A-Za-z]+[-–to]+[A-Za-z]+\s+)?\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)\b|"
        r"(?:(?:Open|Closed|Closes)(?:\s+soon)?(?:\s*[·•\u00b7|\-–]\s*)?)?(?:Closes|Opens|Open)?\s*(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)|24 hours)(?:\s+[A-Za-z]+)?|"
        r"\b(?:Open|Closed)\s+24\s+hours\b",
        re.IGNORECASE,
    )

    CURRENCY_RE = re.compile(
        r"[$€£₹]\s*[\d,]+(?:\.\d+)?(?:[KMBkmb])?(?:/(?:year|yr|month|mo|hour|hr))?"
    )

    RATING_RE = re.compile(
        r"\b([1-5](?:\.\d)?)\s*(?:/\s*5|\bstar[s]?\b|\(\d+\))\b|\b([1-5]\.\d)\b"
    )

    URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)

    ADDRESS_KEYWORDS_RE = re.compile(
        r"\b(street|st|avenue|ave|road|rd|colony|lane|ln|drive|dr|boulevard|blvd|"
        r"highway|expy|nagar|nivas|marg|bldg|building|plaza|floor|suite|apt|room|po\s*box)\b",
        re.IGNORECASE,
    )

    CATEGORY_KEYWORDS_RE = re.compile(
        r"\b(company|agency|services|support|consultant|consultancy|solutions|systems|"
        r"technologies|clinic|hospital|store|center|firm|enterprise|laboratory|labs)\b",
        re.IGNORECASE,
    )

    UI_NOISE_RE = re.compile(
        r"^(?:website|directions|online appointments|share|save|no reviews|\?|[\ue000-\uf8ff\s·•|\-_])+$",
        re.IGNORECASE,
    )

    # Checks if text is likely composite (contains delimiters or explicit key-value pairs)
    DELIM_SPLIT_RE = re.compile(r"\s*[|;·•\n]\s*")
    KEY_VALUE_RE = re.compile(r"^\s*([A-Za-z0-9_\s]{2,30})\s*[:=]\s*(.+)$")

    def is_composite(self, text: str) -> bool:
        """Determine if a cell text contains multiple packed attributes."""
        if not text or len(text) < 10:
            return False
        # Multiple delimiters
        delims = len(self.DELIM_SPLIT_RE.findall(text))
        if delims >= 2:
            return True
        # Key-Value structure
        if self.KEY_VALUE_RE.search(text):
            return True
        # Presence of multiple distinct features
        features = 0
        if self.PHONE_RE.search(text):
            features += 1
        if self.EMAIL_RE.search(text):
            features += 1
        if self.HOURS_RE.search(text):
            features += 1
        if self.CURRENCY_RE.search(text):
            features += 1
        if self.ADDRESS_KEYWORDS_RE.search(text):
            features += 1
        return features >= 2

    def decompose(self, text: str, subject_name: str = "") -> list[DecomposedFact]:
        """Decompose a composite cell into discrete, typed semantic facts."""
        facts: list[DecomposedFact] = []
        seen_preds: set[tuple[str, str]] = set()

        def add_fact(pred: str, val: str, et: str | None = None):
            clean_val = val.strip().strip(".!?,|·• ")
            if not clean_val or len(clean_val) < 2:
                return
            key = (pred, clean_val.lower())
            if key not in seen_preds:
                seen_preds.add(key)
                facts.append(DecomposedFact(predicate=pred, value=clean_val, entity_type=et))

        # Split cell into candidate chunks
        chunks = [c.strip() for c in self.DELIM_SPLIT_RE.split(text) if c.strip()]
        if not chunks:
            chunks = [text.strip()]

        subj_lower = subject_name.strip().lower()

        for chunk in chunks:
            # 1. Check if chunk is pure UI noise or duplicate subject name
            if self.UI_NOISE_RE.match(chunk):
                continue
            chunk_lower = chunk.lower()
            if subj_lower and (chunk_lower == subj_lower or chunk_lower.startswith(subj_lower + " ")):
                # If chunk is solely the subject name or subject name duplicated, skip
                if len(chunk_lower) <= len(subj_lower) + 3:
                    continue

            # 2. Check for explicit 'Key: Value' pattern (e.g., 'Emergency Contact: +91...', 'Office: Building 4')
            kv_match = self.KEY_VALUE_RE.match(chunk)
            if kv_match:
                k, v = kv_match.group(1).strip(), kv_match.group(2).strip()
                norm_pred = normalize_header_to_predicate(k)
                # Check value entity type
                if self.EMAIL_RE.search(v):
                    add_fact(norm_pred, v, "EMAIL_ADDRESS")
                elif self.PHONE_RE.search(v):
                    add_fact(norm_pred, v, "PHONE_NUMBER")
                elif self.CURRENCY_RE.search(v):
                    salary_pred = "HAS_SALARY" if norm_pred in ("HAS_BASE", "HAS_PAY", "HAS_WAGE", "HAS_COMPENSATION") else norm_pred
                    add_fact(salary_pred, v, "SALARY")
                else:
                    add_fact(norm_pred, v, None)
                continue

            # 3. Universal Entity Pattern Matching on the chunk
            # Phone Number
            phone_m = self.PHONE_RE.search(chunk)
            if phone_m:
                phone_val = phone_m.group(0).strip()
                add_fact("HAS_PHONE", phone_val, "PHONE_NUMBER")
                # Remove phone from chunk so remaining text can be evaluated
                chunk = (chunk[:phone_m.start()] + " " + chunk[phone_m.end():]).strip()

            # Email Address
            email_m = self.EMAIL_RE.search(chunk)
            if email_m:
                email_val = email_m.group(0).strip()
                add_fact("HAS_EMAIL", email_val, "EMAIL_ADDRESS")
                chunk = (chunk[:email_m.start()] + " " + chunk[email_m.end():]).strip()

            # Operating Hours
            hours_m = self.HOURS_RE.search(chunk)
            if hours_m:
                hours_val = hours_m.group(0).strip()
                # Clean up punctuation
                hours_val = re.sub(r"[·•|]", ",", hours_val).strip(", ")
                add_fact("HAS_HOURS", hours_val, None)
                chunk = (chunk[:hours_m.start()] + " " + chunk[hours_m.end():]).strip()

            # Currency / Salary
            curr_m = self.CURRENCY_RE.search(chunk)
            if curr_m:
                add_fact("HAS_SALARY", curr_m.group(0).strip(), "SALARY")
                chunk = (chunk[:curr_m.start()] + " " + chunk[curr_m.end():]).strip()

            # URL
            url_m = self.URL_RE.search(chunk)
            if url_m:
                add_fact("HAS_LINK", url_m.group(0).strip(), None)
                chunk = (chunk[:url_m.start()] + " " + chunk[url_m.end():]).strip()

            # Address
            if self.ADDRESS_KEYWORDS_RE.search(chunk):
                add_fact("HAS_ADDRESS", chunk, "LOCATION")
                continue

            # Category / Industry
            if self.CATEGORY_KEYWORDS_RE.search(chunk) and len(chunk.split()) <= 5:
                add_fact("HAS_CATEGORY", chunk, None)
                continue

            # Rating
            rating_m = self.RATING_RE.search(chunk)
            if rating_m and len(chunk) <= 12:
                rate_val = rating_m.group(1) or rating_m.group(2)
                add_fact("HAS_RATING", rate_val, None)
                continue

            # 4. Residual text (if long enough and not noise)
            clean_resid = chunk.strip().strip(".!?,|·• ")
            if clean_resid and len(clean_resid) >= 6 and not self.UI_NOISE_RE.match(clean_resid):
                add_fact("HAS_DETAILS", clean_resid, None)

        return facts
