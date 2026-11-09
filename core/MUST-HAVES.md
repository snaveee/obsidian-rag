---
title: "obsidian-rag Core Requirements (Must-Haves)"
summary: "Non-negotiable functional requirements for obsidian-rag, detailing hybrid search, Markdown parsing, local AI processing, citation-backed QA, and search history telemetry."
keywords:
  - "hybrid-retrieval"
  - "obsidian-vault"
  - "local-ai"
  - "citation-qa"
  - "reranking"
---

# obsidian-rag Core Requirements (Must-Haves)

## 1. Search & Retrieval Engine
- **Hybrid Retrieval:** Executes multi-stage search combining SQLite FTS5 (BM25 sparse) and ChromaDB (dense semantic vectors).
- **Reciprocal Rank Fusion (RRF):** Fuses rank lists using $k=60$ to avoid arbitrary score normalization issues.
- **Cross-Encoder Re-ranking:** Re-scores top candidates using `BAAI/bge-reranker-base` for maximum precision.
- **Graceful Degradation:** Falls back to keyword-only search if dense embeddings or Ollama are unavailable.

## 2. Ingestion & Markdown Parsing
- **Heading-Aware Chunking:** Respects section boundaries with contextual breadcrumbs (`Title > H1 > H2`).
- **Metadata Extraction:** Extracts YAML frontmatter, tags (frontmatter + `#tag`), aliases, and `[[wikilinks]]`.
- **Code Block Isolation:** Masks code fences so `#comments` or links inside code are not mistaken for metadata.
- **Incremental Sync:** Detects file changes via SHA-256 and only re-indexes modified notes.

## 3. Generative Grounding & Safety
- **Strict Grounding:** Restricts answer synthesis strictly to the retrieved context block.
- **Prompt Injection Defense:** Frames context as untrusted reference data; rejects directives inside notes.
- **Inline Citations:** Synthesizes `[1]` numerical citations mapped to verified source references.
- **Sentinel on Missing Data:** Returns "The answer is not found in the provided notes." when context is insufficient.

## 4. Telemetry & User Experience
- **Search History Logging:** Persists query events to SQLite with distinct deduplication.
- **Graph Traversal:** Resolves 1-hop outgoing links and backlinks for cited notes.
- **Modern UI:** Responsive Streamlit interface with scope filters and source inspection.

