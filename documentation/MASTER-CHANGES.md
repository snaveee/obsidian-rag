# Master Changelog & Architectural Timeline — obsidian-rag

This document provides the unified master timeline for the `obsidian-rag` project, recording all architectural milestones, implementation details, and system hardening in reverse-chronological order.

---

## [2026-11-09] Core Implementation — Clean-Room Hybrid RAG for Obsidian Vaults
- **Contributor:** Evans (`snaveee`)
- **Task Domain:** Core Architecture, Pipeline Implementation, Search & Frontend Experience
- **Branch:** `main`

### 1. Summary & Intent
- **Objective:** Build an NDA-free, personal-use hybrid Retrieval-Augmented Generation (RAG) system over Obsidian Markdown vaults, designed to showcase production ML engineering and evaluation standards.
- **Key Deliverables:**
  - Implemented heading-aware Markdown parser and sliding-window chunker in `infra/markdown_parser.py` and `infra/chunking.py` preserving contextual breadcrumbs and masking code blocks.
  - Built dual-retrieval storage layer using ChromaDB (`infra/vector_store.py`) for dense embeddings and SQLite FTS5 (`infra/keyword_index.py`) for sparse BM25 scoring with SQL/FTS injection prevention.
  - Implemented Reciprocal Rank Fusion (RRF $k=60$) and Cross-Encoder re-ranking (`BAAI/bge-reranker-base`) in `infra/hybrid_search.py` and `infra/reranking.py`, with graceful fallback to keyword-only search.
  - Created prompt-injection protected generation engine in `infra/generation.py` synthesizing answers strictly grounded in retrieved notes with numerical citation mapping (`[1]`).
  - Authored SQLite note registry and 1-hop wikilink graph resolver in `infra/note_registry.py`.
  - Added telemetry and search history logger with distinct query deduplication in `infra/history_store.py`.
  - Built FastAPI authenticated backend (`infra/main.py`) and Streamlit interactive dashboard (`streamlit_app.py`).
  - Included curated 8-note sample vault in `sample_vault/` and comprehensive offline test suite.

### 2. Files Added
- `core/PROJECT-CONTEXT.md`: System mission, problem statement, and technical architecture.
- `core/MUST-HAVES.md`: Core system requirements and safety invariants.
- `core/FILE-DEFINITIONS.md`: Comprehensive module catalog and directory map.
- `core/dependencies.txt`: Core python requirements.
- `infra/config.py`: Environment configuration and path resolution.
- `infra/auth.py`: Constant-time API key verification.
- `infra/sqlite_utils.py`: SQLite connection context manager.
- `infra/vault_loader.py`: Filesystem scanner with path escape protection.
- `infra/markdown_parser.py`: YAML frontmatter, `#tag`, and `[[wikilink]]` extraction.
- `infra/chunking.py`: Heading-delimited sliding window chunker.
- `infra/note_registry.py`: SQLite note store and graph link resolver.
- `infra/embeddings.py`: Ollama embedding client with nomic prefixes.
- `infra/vector_store.py`: ChromaDB persistent client wrapper.
- `infra/keyword_index.py`: SQLite FTS5 full-text search with BM25 ranking.
- `infra/reranking.py`: Cross-Encoder reranker.
- `infra/hybrid_search.py`: Reciprocal Rank Fusion hybrid search engine.
- `infra/indexing.py`: Incremental SHA-256 vault indexer.
- `infra/generation.py`: Grounded answer generator with citations.
- `infra/history_store.py`: SQLite search telemetry.
- `infra/main.py`: FastAPI application.
- `streamlit_app.py`: Streamlit dashboard.
- `sample_vault/`: Realistic 8-note demo vault.

