"""Triple extraction from tokenized sentences.

Extracts Subject-Predicate-Object triples using a lightweight
dependency-parsing approach with support for canonical predicates,
row-scoped table extraction, and coreference resolution.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from app.tokenization.token_codec import TOKEN_PATTERN


@dataclass
class Triple:
    """A Subject-Predicate-Object triple extracted from a sentence."""

    subject: str
    predicate: str
    object: str
    source_sentence: str = ""
    doc_id: str = ""


# Canonical predicates mapped from verb phrases and attributes (longest phrase first)
VERB_MAP: dict[str, str] = {
    "manages a budget of": "MANAGES_BUDGET",

    "reports to": "REPORTS_TO",
    "reporting to": "REPORTS_TO",
    "works for": "WORKS_FOR",
    "working for": "WORKS_FOR",
    "works in": "IN_DEPARTMENT",
    "working in": "IN_DEPARTMENT",
    "has home address": "HAS_ADDRESS",
    "has address": "HAS_ADDRESS",
    "lives at": "HAS_ADDRESS",
    "resides at": "HAS_ADDRESS",
    "was hired on": "HIRED_ON",
    "hired on": "HIRED_ON",
    "has ssn": "HAS_SSN",
    "has salary": "HAS_SALARY",
    "has compensation": "HAS_SALARY",
    "has email": "HAS_EMAIL",
    "has contact": "HAS_CONTACT",
    "has phone": "HAS_PHONE",
    "has reason": "HAS_REASON",
    "has role": "HAS_ROLE",
    "has title": "HAS_ROLE",
    "offered a retention bonus equal to": "HAS_RETENTION_BONUS",
    "offered a retention package of": "HAS_RETENTION_BONUS",
    "retention bonus equal to": "HAS_RETENTION_BONUS",
    "retention package of": "HAS_RETENTION_BONUS",
    "promoted to": "PROMOTED_TO",
    "earns": "HAS_SALARY",
    "earning": "HAS_SALARY",
    "earned": "HAS_SALARY",
    "manages": "MANAGES",
    "manage": "MANAGES",
    "managing": "MANAGES",
    "leads": "LEADS",
    "leading": "LEADS",
    "oversees": "OVERSEES",
    "overseeing": "OVERSEES",
    "supervises": "SUPERVISES",
    "supervising": "SUPERVISES",
    "owns": "OWNS",
    "owning": "OWNS",
    "contacts": "HAS_CONTACT",
    "contact": "HAS_CONTACT",
    "is a": "HAS_ROLE",
    "is an": "HAS_ROLE",
    "is": "IS_A",
    "are": "IS_A",
    "was": "IS_A",
    "has": "HAS",
    "have": "HAS",
    "having": "HAS",
}

PRONOUNS = {"he", "she", "they", "it", "this", "the employee", "the individual", "the engineer", "the manager"}


class TripleExtractor:
    """Extracts Subject-Predicate-Object triples from tokenized sentences."""

    def extract(
        self,
        tokenized_sentence: str,
        doc_id: str = "",
        prev_subject: str | None = None,
    ) -> list[Triple]:
        """Extract SVO triples from a tokenized sentence.

        Args:
            tokenized_sentence: Sentence with PII replaced by tokens.
            doc_id: Source document identifier.
            prev_subject: Primary subject token from preceding sentence for coreference.

        Returns:
            List of extracted triples without cross-row cartesian contamination.
        """
        triples: list[Triple] = []
        tokens_in_sentence = TOKEN_PATTERN.findall(tokenized_sentence)
        sentence_lower = tokenized_sentence.lower().strip()

        # Check if sentence begins with a pronoun referring to previous subject
        starts_with_pronoun = any(
            sentence_lower.startswith(p + " ") or sentence_lower.startswith(p + ",")
            for p in PRONOUNS
        )

        effective_subject = None
        if starts_with_pronoun and prev_subject:
            effective_subject = prev_subject
        elif tokens_in_sentence:
            effective_subject = tokens_in_sentence[0]

        # Break compound sentences by clauses (e.g., 'and', 'but', ';')
        clauses = re.split(r"\b(?:and|but|while|also|furthermore)\b|;", tokenized_sentence, flags=re.IGNORECASE)

        for clause in clauses:
            clause_lower = clause.lower().strip()
            clause_tokens = TOKEN_PATTERN.findall(clause)

            for verb_phrase, predicate in VERB_MAP.items():
                if verb_phrase in clause_lower:
                    verb_pos = clause_lower.index(verb_phrase)

                    before_tokens = [
                        t for t in clause_tokens if clause.index(t) < verb_pos
                    ]
                    after_tokens = [
                        t for t in clause_tokens if clause.index(t) > verb_pos
                    ]

                    # Use effective_subject if no token exists before the verb in this clause
                    subj = before_tokens[0] if before_tokens else effective_subject

                    if subj:
                        if predicate == "HAS_ADDRESS":
                            text_after = clause[verb_pos + len(verb_phrase):].strip().strip(".!?,")
                            if text_after:
                                triples.append(
                                    Triple(
                                        subject=subj,
                                        predicate=predicate,
                                        object=text_after,
                                        source_sentence=tokenized_sentence,
                                        doc_id=doc_id,
                                    )
                                )
                        elif after_tokens:
                            # Avoid cartesian explosion: link subject to each object directly
                            for obj in after_tokens:
                                if subj != obj:
                                    triples.append(
                                        Triple(
                                            subject=subj,
                                            predicate=predicate,
                                            object=obj,
                                            source_sentence=tokenized_sentence,
                                            doc_id=doc_id,
                                        )
                                    )
                        else:
                            # Support non-token text objects (e.g. 'has reason Q3 Merit')
                            text_after = clause[verb_pos + len(verb_phrase):].strip().strip(".!?,")
                            # Strip trailing qualifier words like "department" for IN_DEPARTMENT
                            clean_text_after = re.sub(r"\s+department\b", "", text_after, flags=re.IGNORECASE).strip()
                            if clean_text_after and len(clean_text_after) < 100:
                                triples.append(
                                    Triple(
                                        subject=subj,
                                        predicate=predicate,
                                        object=clean_text_after,
                                        source_sentence=tokenized_sentence,
                                        doc_id=doc_id,
                                    )
                                )
                    break  # Matched highest-priority verb phrase in this clause


        # Fallback 1: Whole sentence verb scan if no clause triples found
        if not triples and effective_subject:
            for verb_phrase, predicate in VERB_MAP.items():
                if verb_phrase in sentence_lower:
                    verb_pos = sentence_lower.index(verb_phrase)
                    if predicate == "HAS_ADDRESS":
                        text_after = tokenized_sentence[verb_pos + len(verb_phrase):].strip().strip(".!?,")
                        if text_after:
                            triples.append(
                                Triple(
                                    subject=effective_subject,
                                    predicate=predicate,
                                    object=text_after,
                                    source_sentence=tokenized_sentence,
                                    doc_id=doc_id,
                                )
                            )
                    else:
                        after_tokens = [
                            t for t in tokens_in_sentence if tokenized_sentence.index(t) > verb_pos
                        ]
                        if after_tokens:
                            for obj in after_tokens:
                                if effective_subject != obj:
                                    triples.append(
                                        Triple(
                                            subject=effective_subject,
                                            predicate=predicate,
                                            object=obj,
                                            source_sentence=tokenized_sentence,
                                            doc_id=doc_id,
                                        )
                                    )
                        else:
                            text_after = tokenized_sentence[verb_pos + len(verb_phrase):].strip().strip(".!?,")
                            clean_text_after = re.sub(r"\s+department\b", "", text_after, flags=re.IGNORECASE).strip()
                            if clean_text_after and len(clean_text_after) < 100:
                                triples.append(
                                    Triple(
                                        subject=effective_subject,
                                        predicate=predicate,
                                        object=clean_text_after,
                                        source_sentence=tokenized_sentence,
                                        doc_id=doc_id,
                                    )
                                )
                    break

        # Narrative extraction for executive retention terms (Section 8 prose)
        if "retention bonus" in sentence_lower or "retention package" in sentence_lower:
            ret_match = re.search(
                r"(?:retention\s+bonus\s+equal\s+to|retention\s+package\s+of)\s+([^,.]+)",
                tokenized_sentence,
                re.IGNORECASE,
            )
            if ret_match:
                ret_val = ret_match.group(1).strip()
                if "deal close" in sentence_lower and "deal close" not in ret_val.lower():
                    ret_val = f"{ret_val} upon deal close"

                if "chief executive officer" in sentence_lower or "ceo" in sentence_lower:
                    triples.append(Triple(subject="CEO", predicate="HAS_RETENTION_BONUS", object=ret_val, source_sentence=tokenized_sentence, doc_id=doc_id))
                if "chief financial officer" in sentence_lower or "cfo" in sentence_lower:
                    triples.append(Triple(subject="CFO", predicate="HAS_RETENTION_BONUS", object=ret_val, source_sentence=tokenized_sentence, doc_id=doc_id))
                if "chief operating officer" in sentence_lower or "coo" in sentence_lower:
                    triples.append(Triple(subject="COO", predicate="HAS_RETENTION_BONUS", object=ret_val, source_sentence=tokenized_sentence, doc_id=doc_id))

                for t in tokens_in_sentence:
                    triples.append(Triple(subject=t, predicate="HAS_RETENTION_BONUS", object=ret_val, source_sentence=tokenized_sentence, doc_id=doc_id))


        # Fallback 2: Subject-to-properties proximity link (hub-and-spoke, never pairwise chain)
        if not triples and len(tokens_in_sentence) >= 2:
            primary_subject = tokens_in_sentence[0]
            for obj in tokens_in_sentence[1:]:
                triples.append(
                    Triple(
                        subject=primary_subject,
                        predicate="RELATED_TO",
                        object=obj,
                        source_sentence=tokenized_sentence,
                        doc_id=doc_id,
                    )
                )
        elif not triples and len(tokens_in_sentence) == 1 and starts_with_pronoun and prev_subject and prev_subject != tokens_in_sentence[0]:
            triples.append(
                Triple(
                    subject=prev_subject,
                    predicate="RELATED_TO",
                    object=tokens_in_sentence[0],
                    source_sentence=tokenized_sentence,
                    doc_id=doc_id,
                )
            )

        return triples
