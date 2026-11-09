"""Unit tests for ChromaDB vector store wrapper."""

from infra.chunking import Chunk
from infra.vector_store import VectorStore


def test_vector_store_upsert_and_search(test_vector_store: VectorStore):
    chunks = [
        Chunk("v1:0", "v1", 0, "First chunk vector", "Path 1", 1, 2),
        Chunk("v2:0", "v2", 0, "Second chunk vector", "Path 2", 3, 4),
    ]
    # Unit vectors
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]

    test_vector_store.upsert_chunks(chunks, embeddings, note_title="Vector Test Note")
    assert test_vector_store.count() == 2

    # Query closest to v1 [1, 0, 0]
    hits = test_vector_store.search([1.0, 0.1, 0.0], top_k=2)
    assert len(hits) == 2
    assert hits[0].chunk_id == "v1:0"
    assert hits[0].score > 0.95

    # Test filtering by allowed_note_ids
    filtered = test_vector_store.search([1.0, 0.0, 0.0], top_k=2, allowed_note_ids={"v2"})
    assert len(filtered) == 1
    assert filtered[0].note_id == "v2"


def test_vector_store_delete(test_vector_store: VectorStore):
    chunk = Chunk("del_v:0", "del_v", 0, "Delete chunk vector", "Path", 1, 2)
    test_vector_store.upsert_chunks([chunk], [[0.5, 0.5, 0.0]], note_title="To Delete")
    assert test_vector_store.count() == 1

    test_vector_store.delete_note_chunks("del_v")
    assert test_vector_store.count() == 0

