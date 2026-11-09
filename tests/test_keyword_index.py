"""Unit tests for SQLite FTS5 sparse text search and BM25 ranking."""

from infra.chunking import Chunk
from infra.keyword_index import KeywordStore, sanitize_fts_query


def test_sanitize_fts_query():
    # Quotes and special syntax should be sanitized
    assert sanitize_fts_query('vector "search": test*') == '"vector" OR "search" OR "test"'
    assert sanitize_fts_query('   ') == ""
    assert sanitize_fts_query('single') == '"single"'


def test_keyword_store_search_and_filter(test_keyword_store: KeywordStore):
    chunks = [
        Chunk("note1:0", "note1", 0, "Reciprocal rank fusion combines rank lists without scores.", "RRF", 1, 5),
        Chunk("note2:0", "note2", 0, "ChromaDB stores high dimensional dense vectors.", "VectorDB", 1, 5),
        Chunk("note3:0", "note3", 0, "Cross encoder rerank scores token cross-attention.", "Rerank", 1, 5),
    ]

    test_keyword_store.upsert_chunks(chunks[:1], "RRF Note")
    test_keyword_store.upsert_chunks(chunks[1:2], "Chroma Note")
    test_keyword_store.upsert_chunks(chunks[2:], "Rerank Note")

    assert test_keyword_store.count() == 3

    # Search for reciprocal rank
    hits = test_keyword_store.search("reciprocal rank fusion", top_k=5)
    assert len(hits) >= 1
    assert hits[0].chunk_id == "note1:0"
    assert "reciprocal" in hits[0].text.lower()

    # Search with allowed_note_ids filter
    filtered_hits = test_keyword_store.search("scores", top_k=5, allowed_note_ids={"note3"})
    assert len(filtered_hits) == 1
    assert filtered_hits[0].note_id == "note3"


def test_keyword_store_delete(test_keyword_store: KeywordStore):
    chunk = Chunk("del_note:0", "del_note", 0, "Delete me please.", "Del", 1, 2)
    test_keyword_store.upsert_chunks([chunk], "Del Note")
    assert test_keyword_store.count() == 1

    test_keyword_store.delete_note_chunks("del_note")
    assert test_keyword_store.count() == 0

