"""Triple extraction from tokenized sentences.

Extracts Subject-Predicate-Object triples using a lightweight
dependency-parsing approach. For the MVP, uses regex heuristics
to avoid requiring the heavy spaCy transformer model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.tokenization.token_codec import TOKEN_PATTERN


@dataclass
class Triple:
    """A Subject-Predicate-Object triple extracted from a sentence."""

    subject: str
    predicate: str
    object: str
    source_sentence: str = ""
    doc_id: str = ""


# Common relationship verbs and their canonical predicates
VERB_MAP: dict[str, str] = {
    "manages": "MANAGES",
    "manage": "MANAGES",
    "managing": "MANAGES",
    "reports to": "REPORTS_TO",
    "reporting to": "REPORTS_TO",
    "earns": "EARNS",
    "earning": "EARNS",
    "earned": "EARNS",
    "leads": "LEADS",
    "leading": "LEADS",
    "works for": "WORKS_FOR",
    "working for": "WORKS_FOR",
    "oversees": "OVERSEES",
    "overseeing": "OVERSEES",
    "supervises": "SUPERVISES",
    "supervising": "SUPERVISES",
    "owns": "OWNS",
    "owning": "OWNS",
    "has": "HAS",
    "have": "HAS",
    "having": "HAS",
    "is": "IS_A",
    "are": "IS_A",
    "was": "IS_A",
    "contacts": "HAS_CONTACT",
    "contact": "HAS_CONTACT",
}


PRONOUNS = {"he", "she", "they", "it", "this", "the employee", "the individual", "the engineer", "the manager"}


class TripleExtractor:
    """Extracts Subject-Predicate-Object triples from tokenized sentences.

    Uses a lightweight regex + heuristic approach for the MVP with pronoun
    coreference resolution and clause handling.
    """

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
            List of extracted triples.
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

                    # If no token before verb in this clause, use the effective subject (coreference)
                    if not before_tokens and effective_subject:
                        before_tokens = [effective_subject]

                    for subj in before_tokens:
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

        # Fallback 1: Whole sentence verb scan if no clause triples found
        if not triples and len(tokens_in_sentence) >= 2:
            for verb_phrase, predicate in VERB_MAP.items():
                if verb_phrase in sentence_lower:
                    verb_pos = sentence_lower.index(verb_phrase)
                    before_tokens = [
                        t for t in tokens_in_sentence if tokenized_sentence.index(t) < verb_pos
                    ]
                    after_tokens = [
                        t for t in tokens_in_sentence if tokenized_sentence.index(t) > verb_pos
                    ]
                    for subj in before_tokens:
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

        # Fallback 2: Proximity-based links
        if not triples and len(tokens_in_sentence) >= 2:
            for i in range(len(tokens_in_sentence) - 1):
                triples.append(
                    Triple(
                        subject=tokens_in_sentence[i],
                        predicate="RELATED_TO",
                        object=tokens_in_sentence[i + 1],
                        source_sentence=tokenized_sentence,
                        doc_id=doc_id,
                    )
                )
        elif not triples and len(tokens_in_sentence) == 1 and effective_subject and effective_subject != tokens_in_sentence[0]:
            triples.append(
                Triple(
                    subject=effective_subject,
                    predicate="RELATED_TO",
                    object=tokens_in_sentence[0],
                    source_sentence=tokenized_sentence,
                    doc_id=doc_id,
                )
            )

        return triples
