"""Unit tests for CrossEncoder reranker wrapper and fallback logic."""

from infra.reranking import rerank_results


def test_rerank_results_empty():
    res, applied = rerank_results("query", [], top_k=5)
    assert res == []
    assert applied is False


def test_rerank_fallback_on_invalid_model():
    candidates = [
        {"chunk_id": "c1", "text": "First passage"},
        {"chunk_id": "c2", "text": "Second passage"},
    ]
    # Pointing to an invalid model name should trigger fallback without exception
    res, applied = rerank_results(
        query="test query",
        candidates=candidates,
        top_k=2,
        model_name="non-existent/invalid-model-xyz-123",
    )
    assert len(res) == 2
    assert applied is False
    assert res[0]["chunk_id"] == "c1"

