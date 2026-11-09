"""Live end-to-end integration test against running local Ollama instance.

Skipped automatically unless ORAG_LIVE=1 environment variable is set.
"""

import os
import requests
import pytest
from infra.config import load_settings
from infra.embeddings import EmbeddingClient
from infra.generation import generate_answer
from infra.hybrid_search import HybridSearchEngine
from infra.indexing import VaultIndexer
from infra.keyword_index import KeywordStore
from infra.note_registry import NoteRegistry
from infra.vector_store import VectorStore

LIVE_ENABLED = os.getenv("ORAG_LIVE", "0") in {"1", "true", "yes"}


def is_ollama_reachable(url: str) -> bool:
    try:
        r = requests.get(f"{url.rstrip('/')}/api/tags", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not LIVE_ENABLED, reason="Live test skipped; set ORAG_LIVE=1 to run.")
def test_live_indexing_and_grounded_qa(temp_dir):
    settings = load_settings()
    if not is_ollama_reachable(settings.ollama_url):
        pytest.skip(f"Ollama not reachable at {settings.ollama_url}")

    registry = NoteRegistry(temp_dir / "live_reg.sqlite3")
    keyword_store = KeywordStore(temp_dir / "live_fts.sqlite3")
    vector_store = VectorStore(temp_dir / "live_chroma", collection_name="live_test")
    embedder = EmbeddingClient(settings.ollama_url, model=settings.embed_model)

    indexer = VaultIndexer(
        vault_path=settings.vault_path,
        registry=registry,
        keyword_store=keyword_store,
        vector_store=vector_store,
        embedding_client=embedder,
    )

    # 1. Index sample vault
    report = indexer.sync(full_reindex=True)
    assert report.total_notes > 0

    # 2. Search
    engine = HybridSearchEngine(
        registry=registry,
        keyword_store=keyword_store,
        vector_store=vector_store,
        embedding_client=embedder,
        rerank_enabled=True,
    )
    query = "How does reciprocal rank fusion combine search results?"
    results, mode, rerank_applied = engine.search(query=query, top_k=3)
    assert len(results) > 0
    assert mode == "hybrid"

    # 3. Grounded generation
    ans = generate_answer(
        query=query,
        results=results,
        ollama_url=settings.ollama_url,
        model=settings.gen_model,
    )
    assert ans.answer
    assert ans.answer != "The answer is not found in the provided notes."
    assert len(ans.sources) > 0

