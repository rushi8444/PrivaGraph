"""Local full-text index for privacy-tokenized document passages."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Iterable


class PassageStore:
    """Persist and search safe document passages using SQLite FTS5 when available."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fts_enabled = True
        with self._connect() as conn:
            try:
                conn.execute(
                    """CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(
                        text, doc_id UNINDEXED, ordinal UNINDEXED,
                        tokenize='porter unicode61 remove_diacritics 2'
                    )"""
                )
            except sqlite3.OperationalError:
                # Keep the feature usable on SQLite builds without FTS5.
                self._fts_enabled = False
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS passages (
                        id INTEGER PRIMARY KEY,
                        text TEXT NOT NULL,
                        doc_id TEXT NOT NULL,
                        ordinal INTEGER NOT NULL
                    )"""
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_passages_doc_id ON passages(doc_id)"
                )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _make_passages(sentences: Iterable[str], max_chars: int = 1100) -> list[str]:
        """Group adjacent safe sentences into passages with one-sentence overlap."""
        passages: list[str] = []
        current: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence = " ".join(str(sentence).split())
            if not sentence:
                continue
            if current and current_length + len(sentence) + 1 > max_chars:
                passages.append(" ".join(current))
                overlap = current[-1]
                current = [overlap]
                current_length = len(overlap)
            current.append(sentence)
            current_length += len(sentence) + 1

        if current:
            passages.append(" ".join(current))
        return passages

    def index_document(self, doc_id: str, safe_sentences: Iterable[str]) -> int:
        """Replace a document's indexed passages; callers must pass tokenized text."""
        passages = self._make_passages(safe_sentences)
        with self._connect() as conn:
            old_rows = conn.execute(
                "SELECT rowid FROM passages WHERE doc_id = ?", (doc_id,)
            ).fetchall()
            conn.executemany(
                "DELETE FROM passages WHERE rowid = ?",
                [(row["rowid"],) for row in old_rows],
            )
            conn.executemany(
                "INSERT INTO passages(text, doc_id, ordinal) VALUES (?, ?, ?)",
                [(text, doc_id, i) for i, text in enumerate(passages)],
            )
        return len(passages)

    def remove_document(self, doc_id: str) -> int:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT rowid FROM passages WHERE doc_id = ?", (doc_id,)
            ).fetchall()
            conn.executemany(
                "DELETE FROM passages WHERE rowid = ?",
                [(row["rowid"],) for row in rows],
            )
        return len(rows)

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM passages")

    def search(
        self,
        query_terms: Iterable[str],
        *,
        allowed_doc_ids: set[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, str]]:
        """Return the best matching passages, restricted to the caller's document scope."""
        if allowed_doc_ids is not None and not allowed_doc_ids:
            return []

        terms: list[str] = []
        seen: set[str] = set()
        for value in query_terms:
            # Quote user text as literal FTS terms; never allow query syntax through.
            for term in re.findall(r"[\w]+", value, flags=re.UNICODE):
                normalized = term.casefold()
                if len(normalized) > 1 and normalized not in seen:
                    terms.append(term)
                    seen.add(normalized)
        if not terms:
            return []

        scope_sql = ""
        params: list[object] = []
        if allowed_doc_ids is not None:
            placeholders = ",".join("?" for _ in allowed_doc_ids)
            scope_sql = f" AND doc_id IN ({placeholders})"
            params.extend(sorted(allowed_doc_ids))

        with self._connect() as conn:
            if self._fts_enabled:
                match_query = " OR ".join(f'"{term}"' for term in terms)
                rows = conn.execute(
                    f"""SELECT text, doc_id, bm25(passages) AS score
                        FROM passages WHERE passages MATCH ?{scope_sql}
                        ORDER BY score LIMIT ?""",
                    [match_query, *params, max(1, limit)],
                ).fetchall()
            else:
                conditions = " OR ".join("text LIKE ?" for _ in terms)
                like_params = [f"%{term}%" for term in terms]
                rows = conn.execute(
                    f"""SELECT text, doc_id FROM passages
                        WHERE ({conditions}){scope_sql}
                        ORDER BY ordinal LIMIT ?""",
                    [*like_params, *params, max(1, limit)],
                ).fetchall()

        return [{"text": row["text"], "doc_id": row["doc_id"]} for row in rows]
