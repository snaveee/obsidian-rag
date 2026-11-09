"""SQLite FTS5 sparse text search engine with BM25 ranking.

Provides full-text keyword indexing and search over note chunks, with query
sanitization to prevent FTS syntax injection and support for note_id filtering.
"""

import logging
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from infra.chunking import Chunk
from infra.sqlite_utils import connect

__all__ = ["KeywordSearchResult", "KeywordStore", "sanitize_fts_query"]

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
    chunk_id UNINDEXED,
    note_id UNINDEXED,
    title,
    heading_path,
    text,
    line_start UNINDEXED,
    line_end UNINDEXED,
    tokenize = 'porter unicode61'
);

CREATE TABLE IF NOT EXISTS chunk_fts_meta (
    chunk_id   TEXT PRIMARY KEY,
    note_id    TEXT NOT NULL,
    title      TEXT NOT NULL,
    heading_path TEXT NOT NULL,
    text       TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    line_end   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fts_meta_note ON chunk_fts_meta(note_id);
"""


def sanitize_fts_query(raw_query: str) -> str:
    """Sanitize user query for SQLite FTS5 match expressions.

    Extracts alphanumeric tokens and joins them with OR or AND, preventing
    syntax errors caused by unbalanced quotes, colons, or wildcards.
    """
    clean = re.sub(r"[^\w\s]", " ", raw_query)
    tokens = clean.strip().split()
    if not tokens:
        return ""
    # Enclose each word in double quotes for safe literal matching
    return " OR ".join(f'"{t}"' for t in tokens if len(t) > 1) or f'"{tokens[0]}"'


@dataclass(frozen=True)
class KeywordSearchResult:
    """A scored chunk match from FTS5 BM25 search."""

    chunk_id: str
    note_id: str
    score: float  # Normalized BM25 rank score (higher is better)
    text: str
    metadata: dict[str, Any]


class KeywordStore:
    """SQLite FTS5 full-text storage and BM25 search."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        with connect(self.db_path) as connection:
            connection.executescript(_SCHEMA)

    def upsert_chunks(self, chunks: list[Chunk], note_title: str) -> None:
        """Insert or replace chunks in FTS5 and metadata tables."""
        if not chunks:
            return

        with connect(self.db_path) as conn:
            # Delete old entries first
            chunk_ids = [c.chunk_id for c in chunks]
            conn.executemany("DELETE FROM chunk_fts_meta WHERE chunk_id = ?", [(cid,) for cid in chunk_ids])
            conn.executemany("DELETE FROM chunk_fts WHERE chunk_id = ?", [(cid,) for cid in chunk_ids])

            # Insert metadata table
            meta_rows = [
                (c.chunk_id, c.note_id, note_title, c.heading_path, c.text, c.line_start, c.line_end)
                for c in chunks
            ]
            conn.executemany(
                "INSERT INTO chunk_fts_meta (chunk_id, note_id, title, heading_path, text, line_start, line_end) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                meta_rows,
            )

            # Insert FTS table
            conn.executemany(
                "INSERT INTO chunk_fts (chunk_id, note_id, title, heading_path, text, line_start, line_end) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                meta_rows,
            )

    def delete_note_chunks(self, note_id: str) -> None:
        """Delete all chunks for a note from FTS index."""
        with connect(self.db_path) as conn:
            conn.execute("DELETE FROM chunk_fts WHERE note_id = ?", (note_id,))
            conn.execute("DELETE FROM chunk_fts_meta WHERE note_id = ?", (note_id,))

    def search(
        self,
        query: str,
        top_k: int = 10,
        allowed_note_ids: set[str] | None = None,
    ) -> list[KeywordSearchResult]:
        """Search chunks with BM25 ranking and optional note_id filter."""
        match_expr = sanitize_fts_query(query)
        if not match_expr or top_k <= 0:
            return []

        filter_clause = ""
        params: list[Any] = [match_expr]

        if allowed_note_ids is not None:
            if not allowed_note_ids:
                return []
            placeholders = ", ".join("?" for _ in allowed_note_ids)
            filter_clause = f"AND note_id IN ({placeholders})"
            params.extend(sorted(allowed_note_ids))

        params.append(top_k)

        # FTS5 bm25() returns negative numbers where smaller is more relevant (e.g. -12.4 is better than -2.1)
        sql = f"""
        SELECT chunk_id, note_id, title, heading_path, text, line_start, line_end,
               bm25(chunk_fts) AS bm25_score
        FROM chunk_fts
        WHERE chunk_fts MATCH ? {filter_clause}
        ORDER BY bm25_score ASC
        LIMIT ?;
        """

        results: list[KeywordSearchResult] = []
        try:
            with connect(self.db_path) as conn:
                rows = conn.execute(sql, params).fetchall()

            for r in rows:
                raw_bm25 = float(r["bm25_score"])
                # Invert score so higher is better for rank fusion: score = -raw_bm25
                score = -raw_bm25
                meta = {
                    "chunk_id": r["chunk_id"],
                    "note_id": r["note_id"],
                    "title": r["title"],
                    "heading_path": r["heading_path"],
                    "line_start": r["line_start"],
                    "line_end": r["line_end"],
                }
                results.append(
                    KeywordSearchResult(
                        chunk_id=r["chunk_id"],
                        note_id=r["note_id"],
                        score=score,
                        text=r["text"],
                        metadata=meta,
                    )
                )
        except sqlite3.OperationalError as err:
            logger.warning("FTS search operational error: %s", err)
            return []

        return results

    def get_chunk_text(self, chunk_id: str) -> str | None:
        """Fetch chunk text by ID."""
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT text FROM chunk_fts_meta WHERE chunk_id = ?", (chunk_id,)).fetchone()
            return row["text"] if row else None

    def count(self) -> int:
        """Count of indexed chunks."""
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM chunk_fts_meta").fetchone()
            return row[0] if row else 0

    def reset(self) -> None:
        """Clear all indexed data."""
        with connect(self.db_path) as conn:
            conn.execute("DELETE FROM chunk_fts")
            conn.execute("DELETE FROM chunk_fts_meta")

