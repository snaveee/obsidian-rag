"""SQLite search history and telemetry storage.

Persists user queries, answer previews, and result metrics. Supports distinct
query retrieval (keeping the most recent timestamp) for clean UI replay.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from infra.sqlite_utils import connect

__all__ = ["HistoryEntry", "HistoryStore"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS search_history (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    query            TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    results_count    INTEGER NOT NULL,
    answer_preview   TEXT,
    retrieval_mode   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_created ON search_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_query ON search_history(query);
"""


@dataclass(frozen=True)
class HistoryEntry:
    """A recorded search event."""

    id: int
    query: str
    created_at: str
    results_count: int
    answer_preview: str | None
    retrieval_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "created_at": self.created_at,
            "results_count": self.results_count,
            "answer_preview": self.answer_preview,
            "retrieval_mode": self.retrieval_mode,
        }


class HistoryStore:
    """Manages search history logging and deduplicated retrieval."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        with connect(self.db_path) as conn:
            conn.executescript(_SCHEMA)

    def log_search(
        self,
        query: str,
        results_count: int,
        answer_preview: str | None,
        retrieval_mode: str,
    ) -> int:
        """Insert a search query event and return its ID."""
        clean_q = (query or "").strip()
        if not clean_q:
            return 0

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        preview = (answer_preview or "").strip()[:200]

        with connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO search_history (query, created_at, results_count, answer_preview, retrieval_mode) "
                "VALUES (?, ?, ?, ?, ?)",
                (clean_q, now, results_count, preview, retrieval_mode),
            )
            return cursor.lastrowid or 0

    def list_history(self, limit: int = 20, distinct: bool = True) -> list[HistoryEntry]:
        """Fetch recent search history with optional distinct query deduplication."""
        clamped_limit = max(1, min(limit, 100))

        if distinct:
            # Pick the row with the max id per query to guarantee latest preview and metrics
            sql = """
            SELECT id, query, created_at, results_count, answer_preview, retrieval_mode
            FROM search_history
            WHERE id IN (
                SELECT MAX(id)
                FROM search_history
                GROUP BY query
            )
            ORDER BY created_at DESC, id DESC
            LIMIT ?;
            """
        else:
            sql = """
            SELECT id, query, created_at, results_count, answer_preview, retrieval_mode
            FROM search_history
            ORDER BY created_at DESC, id DESC
            LIMIT ?;
            """

        with connect(self.db_path) as conn:
            rows = conn.execute(sql, (clamped_limit,)).fetchall()

        return [
            HistoryEntry(
                id=r["id"],
                query=r["query"],
                created_at=r["created_at"],
                results_count=r["results_count"],
                answer_preview=r["answer_preview"],
                retrieval_mode=r["retrieval_mode"],
            )
            for r in rows
        ]

    def clear(self) -> None:
        """Clear all search history logs."""
        with connect(self.db_path) as conn:
            conn.execute("DELETE FROM search_history")

