"""Retrieval evaluation and latency benchmarking script for obsidian-rag.

Evaluates retrieval quality (Hit@1, Hit@3, MRR) and execution latency across
different retrieval modes (BM25-only, Hybrid RRF, and Cross-Encoder Re-ranking).
Can run completely offline using BM25 or full hybrid when models are present.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infra.config import load_settings
from infra.embeddings import EmbeddingClient
from infra.hybrid_search import HybridSearchEngine
from infra.indexing import VaultIndexer
from infra.keyword_index import KeywordStore
from infra.note_registry import NoteRegistry
from infra.vector_store import VectorStore

BENCHMARK_QUERIES = [
    {
        "query": "How does reciprocal rank fusion combine search results?",
        "expected_stems": ["03-Reciprocal-Rank-Fusion"],
    },
    {
        "query": "What are the limitations of dense vector search?",
        "expected_stems": ["02-Vector-Databases"],
    },
    {
        "query": "How to prevent code fence comments from being parsed as tags?",
        "expected_stems": ["05-Chunking-Strategies"],
    },
    {
        "query": "What are the core evaluation dimensions for RLHF alignment?",
        "expected_stems": ["06-RLHF-Evaluation-Rubrics"],
    },
    {
        "query": "How to handle CPU bound cross-encoder tasks in async python?",
        "expected_stems": ["07-Python-Async-Patterns"],
    },
]


def run_benchmark(no_llm: bool = False):
    settings = load_settings()
    print("=" * 65)
    print(" obsidian-rag Retrieval & Latency Benchmark")
    print(f" Vault Path: {settings.vault_path}")
    print("=" * 65)

    registry = NoteRegistry(settings.registry_db)
    keyword_store = KeywordStore(settings.keyword_db)
    vector_store = VectorStore(settings.chroma_dir, collection_name=settings.collection_name)
    embedding_client = EmbeddingClient(settings.ollama_url, model=settings.embed_model)

    indexer = VaultIndexer(
        vault_path=settings.vault_path,
        registry=registry,
        keyword_store=keyword_store,
        vector_store=vector_store,
        embedding_client=embedding_client,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    print("\n[1/3] Syncing vault index...")
    t0 = time.perf_counter()
    report = indexer.sync(full_reindex=False)
    t_sync = (time.perf_counter() - t0) * 1000
    print(f" Sync finished in {t_sync:.1f}ms: {report.total_notes} notes, {report.total_chunks} chunks.")

    search_engine = HybridSearchEngine(
        registry=registry,
        keyword_store=keyword_store,
        vector_store=vector_store,
        embedding_client=embedding_client,
        rerank_enabled=not no_llm,
        reranker_model=settings.reranker_model,
    )

    configs = [
        ("BM25 Keyword Only", False),
        ("Hybrid RRF + Rerank", True),
    ]

    print("\n[2/3] Running benchmark queries...")
    for mode_name, enable_rerank in configs:
        hit_1 = 0
        hit_3 = 0
        reciprocal_ranks = []
        latencies = []

        for item in BENCHMARK_QUERIES:
            q = item["query"]
            expected = item["expected_stems"]

            t_start = time.perf_counter()
            results, mode, rerank_applied = search_engine.search(
                query=q,
                top_k=5,
                enable_rerank=enable_rerank if not no_llm else False,
            )
            lat_ms = (time.perf_counter() - t_start) * 1000
            latencies.append(lat_ms)

            # Check positions
            hit_rank = None
            for rank, r in enumerate(results, start=1):
                chunk_id = r.get("chunk_id", "")
                note_id = r.get("note_id", "")
                note_rec = registry.get_note(note_id)
                stem = note_rec.stem if note_rec else ""
                if any(exp.lower() in stem.lower() for exp in expected):
                    hit_rank = rank
                    break

            if hit_rank == 1:
                hit_1 += 1
            if hit_rank and hit_rank <= 3:
                hit_3 += 1
            reciprocal_ranks.append(1.0 / hit_rank if hit_rank else 0.0)

        n = len(BENCHMARK_QUERIES)
        avg_lat = sum(latencies) / n
        mrr = sum(reciprocal_ranks) / n

        print(f"\n--- {mode_name} ---")
        print(f" Hit@1: {hit_1}/{n} ({hit_1/n*100:.1f}%)")
        print(f" Hit@3: {hit_3}/{n} ({hit_3/n*100:.1f}%)")
        print(f" MRR:   {mrr:.4f}")
        print(f" Latency (avg): {avg_lat:.2f}ms")

    print("\n[3/3] Benchmark complete.")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true", help="Bypass cross-encoder and embeddings")
    args = parser.parse_args()
    run_benchmark(no_llm=args.no_llm)

