"""Multi-stage hybrid search combining BM25 keyword search and dense vector search.

Fuses sparse and dense results using Reciprocal Rank Fusion (RRF with k=60),
with optional Cross-Encoder re-ranking. Degrades gracefully to keyword-only
search if embeddings or Ollama are unavailable.
"""

import logging
from typing import Any

from infra.embeddings import EmbeddingClient, EmbeddingUnavailable
from infra.keyword_index import KeywordStore
from infra.note_registry import NoteRegistry
from infra.reranking import rerank_results
from infra.vector_store import VectorStore

__all__ = ["HybridSearchEngine", "SearchResult", "compute_rrf"]

logger = logging.getLogger(__name__)

RRF_K = 60


def compute_rrf(rank_lists: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """Compute Reciprocal Rank Fusion scores across multiple ranked ID lists.

    Formula: score(d) = sum(1.0 / (k + rank)) for each rank list where d appears.
    """
    scores: dict[str, float] = {}
    for rank_list in rank_lists:
        for rank, item_id in enumerate(rank_list, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + (1.0 / (k + rank))
    return scores


class SearchResult:
    """Standardized search hit returned by the hybrid engine."""

    def __init__(
        self,
        chunk_id: str,
        note_id: str,
        title: str,
        heading_path: str,
        text: str,
        line_start: int,
        line_end: int,
        score: float,
        source_mode: str,
        rerank_score: float | None = None,
    ) -> None:
        self.chunk_id = chunk_id
        self.note_id = note_id
        self.title = title
        self.heading_path = heading_path
        self.text = text
        self.line_start = line_start
        self.line_end = line_end
        self.score = score
        self.source_mode = source_mode
        self.rerank_score = rerank_score

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        d = {
            "chunk_id": self.chunk_id,
            "note_id": self.note_id,
            "title": self.title,
            "heading_path": self.heading_path,
            "text": self.text,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "score": round(self.score, 6),
            "source_mode": self.source_mode,
        }
        if self.rerank_score is not None:
            d["rerank_score"] = round(self.rerank_score, 4)
        return d


class HybridSearchEngine:
    """Orchestrates multi-stage hybrid retrieval across sparse and dense indexes."""

    def __init__(
        self,
        registry: NoteRegistry,
        keyword_store: KeywordStore,
        vector_store: VectorStore,
        embedding_client: EmbeddingClient,
        rerank_enabled: bool = True,
        reranker_model: str = "BAAI/bge-reranker-base",
    ) -> None:
        self.registry = registry
        self.keyword_store = keyword_store
        self.vector_store = vector_store
        self.embedding_client = embedding_client
        self.rerank_enabled = rerank_enabled
        self.reranker_model = reranker_model

    def search(
        self,
        query: str,
        top_k: int = 5,
        candidate_k: int = 20,
        tags: list[str] | None = None,
        folder: str | None = None,
        enable_rerank: bool | None = None,
    ) -> tuple[list[dict[str, Any]], str, bool]:
        """Execute hybrid search with fallback to keyword-only mode.

        Returns:
            tuple[list[dict], str, bool]: (results, mode ["hybrid"|"keyword_only"], rerank_applied)
        """
        clean_query = (query or "").strip()
        if not clean_query:
            return [], "empty", False

        # 1. Resolve note_id filters from registry
        allowed_note_ids = self.registry.filter_note_ids(tags=tags, folder=folder)
        if allowed_note_ids is not None and not allowed_note_ids:
            # Filters produced 0 matching notes
            return [], "empty_filter", False

        # 2. Sparse / Keyword Search
        bm25_hits = self.keyword_store.search(
            query=clean_query,
            top_k=candidate_k,
            allowed_note_ids=allowed_note_ids,
        )

        # 3. Dense Vector Search (with graceful fallback)
        vector_hits = []
        mode = "hybrid"
        try:
            query_vector = self.embedding_client.embed_query(clean_query)
            vector_hits = self.vector_store.search(
                query_vector=query_vector,
                top_k=candidate_k,
                allowed_note_ids=allowed_note_ids,
            )
        except (EmbeddingUnavailable, Exception) as exc:
            logger.warning("Vector search unavailable (%s); falling back to keyword-only.", exc)
            mode = "keyword_only"

        # 4. Fusion
        bm25_ids = [h.chunk_id for h in bm25_hits]
        vector_ids = [h.chunk_id for h in vector_hits]

        if mode == "keyword_only" or not vector_ids:
            # Use BM25 order directly
            fused_scores = {cid: 1.0 / (RRF_K + rank) for rank, cid in enumerate(bm25_ids, start=1)}
        else:
            fused_scores = compute_rrf([bm25_ids, vector_ids], k=RRF_K)

        sorted_chunk_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)[
            :candidate_k
        ]

        # 5. Populate chunk metadata
        candidates: list[dict[str, Any]] = []
        for cid in sorted_chunk_ids:
            text = self.keyword_store.get_chunk_text(cid) or ""
            # Find meta from hits
            meta = {}
            for h in bm25_hits:
                if h.chunk_id == cid:
                    meta = h.metadata
                    break
            if not meta:
                for v in vector_hits:
                    if v.chunk_id == cid:
                        meta = v.metadata
                        break

            candidates.append(
                {
                    "chunk_id": cid,
                    "note_id": meta.get("note_id", cid.split(":")[0]),
                    "title": meta.get("title", "Untitled"),
                    "heading_path": meta.get("heading_path", ""),
                    "text": text,
                    "line_start": meta.get("line_start", 1),
                    "line_end": meta.get("line_end", 1),
                    "score": fused_scores[cid],
                    "source_mode": mode,
                }
            )

        # 6. Re-ranking
        should_rerank = self.rerank_enabled if enable_rerank is None else enable_rerank
        rerank_applied = False
        if should_rerank and candidates:
            final_results, rerank_applied = rerank_results(
                query=clean_query,
                candidates=candidates,
                top_k=top_k,
                model_name=self.reranker_model,
            )
        else:
            final_results = candidates[:top_k]

        return final_results, mode, rerank_applied

