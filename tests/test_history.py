"""Unit tests for search history logging and distinct deduplication."""

from pathlib import Path

from infra.history_store import HistoryStore


def test_history_store_log_and_distinct(temp_dir: Path):
    store = HistoryStore(temp_dir / "hist.sqlite3")

    # Log same query 3 times with different previews
    store.log_search("duplicate query", 2, "Preview 1", "hybrid")
    store.log_search("unique query", 1, "Preview A", "hybrid")
    store.log_search("duplicate query", 5, "Preview 2 (latest)", "hybrid")

    # Distinct retrieval: should return 2 entries, with the latest preview for duplicate query
    distinct_entries = store.list_history(limit=10, distinct=True)
    assert len(distinct_entries) == 2
    queries = [e.query for e in distinct_entries]
    assert queries[0] == "duplicate query"
    assert queries[1] == "unique query"
    assert distinct_entries[0].answer_preview == "Preview 2 (latest)"

    # Non-distinct retrieval: should return all 3 entries
    all_entries = store.list_history(limit=10, distinct=False)
    assert len(all_entries) == 3


def test_history_store_limit_clamping(temp_dir: Path):
    store = HistoryStore(temp_dir / "hist.sqlite3")
    store.log_search("q1", 1, "p", "hybrid")
    # Clamp below 1 -> 1
    entries = store.list_history(limit=0)
    assert len(entries) == 1

