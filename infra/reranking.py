"""Cross-Encoder re-ranking using sentence-transformers (e.g. BAAI/bge-reranker-base).

Re-ranks candidate search results by computing fine-grained cross-attention
scores between the query and chunk texts. Falls back gracefully to original
order if the model cannot be loaded.
"""

import logging
from typing import Any

from sentence_transformers import CrossEncoder

__all__ = ["CrossEncoderReranker", "get_reranker", "rerank_results"]

logger = logging.getLogger(__name__)

_RERANKER_CACHE: dict[str, CrossEncoder | None] = {}


def get_reranker(model_name: str = "BAAI/bge-reranker-base") -> CrossEncoder | None:
    """Return a cached CrossEncoder instance for model_name, or None if load fails."""
    global _RERANKER_CACHE

    if model_name in _RERANKER_CACHE:
        return _RERANKER_CACHE[model_name]

    try:
        logger.info("Loading CrossEncoder model: %s", model_name)
        model = CrossEncoder(model_name)
        _RERANKER_CACHE[model_name] = model
        return model
    except Exception as exc:
        logger.warning("Failed to load CrossEncoder (%s): %s. Re-ranking will be bypassed.", model_name, exc)
        _RERANKER_CACHE[model_name] = None
        return None


def rerank_results(
    query: str,
    candidates: list[dict[str, Any]],
    top_k: int = 5,
    model_name: str = "BAAI/bge-reranker-base",
) -> tuple[list[dict[str, Any]], bool]:
    """Re-rank candidate search results using CrossEncoder.

    Returns:
        tuple[list[dict[str, Any]], bool]: (re-ranked results, rerank_applied_flag)
    """
    if not candidates or top_k <= 0:
        return [], False

    model = get_reranker(model_name)
    if model is None:
        return candidates[:top_k], False

    # Prepare pairs: (query, candidate_text)
    pairs = [(query, c.get("text", "")) for c in candidates]

    try:
        scores = model.predict(pairs)
        scored_candidates = []
        for cand, score in zip(candidates, scores):
            item = dict(cand)
            item["rerank_score"] = float(score)
            scored_candidates.append(item)

        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:top_k], True
    except Exception as exc:
        logger.warning("Error during reranking: %s. Returning candidate order.", exc)
        return candidates[:top_k], False

