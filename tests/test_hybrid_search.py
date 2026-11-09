"""Unit tests for HybridSearchEngine, RRF math, and graceful degradation."""

from infra.chunking import Chunk
from infra.hybrid_search import HybridSearchEngine, compute_rrf
from infra.keyword_index import KeywordStore
from infra.note_registry import NoteRecord, NoteRegistry
from infra.vector_store import VectorStore


def test_compute_rrf_math():
    list1 = ["doc_a", "doc_b", "doc_c"]
    list2 = ["doc_b", "doc_a", "doc_d"]

    scores = compute_rrf([list1, list2], k=60)
    # doc_a: 1/(60+1) + 1/(60+2) = 1/61 + 1/62 = 0.016393 + 0.016129 = 0.032522
    # doc_b: 1/(60+2) + 1/(60+1) = identical to doc_a
    # doc_c: 1/(60+3) = 0.015873
    assert scores["doc_a"] > scores["doc_c"]
    assert abs(scores["doc_a"] - scores["doc_b"]) < 1e-6


def test_hybrid_search_degrades_to_keyword_when_embedding_fails(
    test_registry: NoteRegistry,
    test_keyword_store: KeywordStore,
    test_vector_store: VectorStore,
):
    class FailingEmbedder:
        def embed_query(self, query: str):
            raise RuntimeError("Ollama connection refused.")

    # Setup 1 note in stores
    rec = NoteRecord.build("note1.md", "Note Title", "sha", [], [], 1)
    test_registry.upsert_note(rec, [])
    c = Chunk("note1:0", rec.note_id, 0, "Keyword matching content about algorithms.", "Head", 1, 3)
    test_keyword_store.upsert_chunks([c], "Note Title")

    engine = HybridSearchEngine(
        registry=test_registry,
        keyword_store=test_keyword_store,
        vector_store=test_vector_store,
        embedding_client=FailingEmbedder(),  # Will fail
        rerank_enabled=False,
    )

    results, mode, rerank_applied = engine.search("algorithms", top_k=5)
    assert mode == "keyword_only"
    assert rerank_applied is False
    assert len(results) == 1
    assert results[0]["chunk_id"] == "note1:0"

