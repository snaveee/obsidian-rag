---
title: System Architecture & Hybrid Retrieval Engine
tags: [architecture, rag, search]
aliases: [System Arch, Overall Architecture]
---

# System Architecture & Hybrid Retrieval Engine

The obsidian-rag system implements a multi-stage retrieval-augmented generation (RAG) architecture optimized for Obsidian knowledge vaults.

## Pipeline Overview

1. **Vault Ingestion**: Markdown files are read, frontmatter parsed, wikilinks extracted, and sections chunked using heading boundaries.
2. **Dual Indexing**:
   - Sparse index: SQLite FTS5 with BM25 scoring for exact keyword matching.
   - Dense index: ChromaDB storing embeddings generated via local Ollama models (such as `nomic-embed-text`).
3. **Hybrid Search & Fusion**: Candidate passages from BM25 and vector search are merged using [[Reciprocal-Rank-Fusion]] (RRF).
4. **Re-ranking**: Top fused candidates pass through [[Cross-Encoder-Reranking]] to calculate token-level interaction scores.
5. **Grounded Generation**: Local LLMs synthesize answers strictly based on retrieved context passages with numerical citations.

## Integration Points

The system connects dense representations stored in [[Vector-Databases]] with structural links between notes.

