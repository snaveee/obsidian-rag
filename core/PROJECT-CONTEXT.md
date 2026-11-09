---
title: "obsidian-rag Project Context & System Architecture"
summary: "Project overview and operational context for obsidian-rag, detailing personal Obsidian knowledge retrieval, hybrid BM25 + dense search, cross-encoder reranking, and citation-backed answer generation."
keywords:
  - "obsidian-rag"
  - "personal-knowledge-base"
  - "second-brain"
  - "rag"
  - "hybrid-search"
  - "semantic-retrieval"
  - "local-ai"
---

# obsidian-rag Project Context & System Architecture

## 1. Executive Summary
- **System Name:** obsidian-rag (Personal Second-Brain Knowledge Copilot).
- **Target Domain:** Personal knowledge vaults, technical dev logs, research notes, and architectural documentation created in Obsidian.
- **Core Functionality:** Local, privacy-first Retrieval-Augmented Generation (RAG) providing hybrid keyword (BM25) and dense semantic vector search, Reciprocal Rank Fusion (RRF), Cross-Encoder re-ranking, and citation-grounded answer generation.
- **Architectural Scope & Boundary:** Operates strictly over local Markdown files. Integrates ChromaDB for dense embeddings and SQLite FTS5 for sparse keyword search. No third-party data egress; completely local using Ollama.

## 2. Problem Statement
- **Fragmented Personal Knowledge:** Developers and researchers amass hundreds of interconnected Markdown notes over years, making keyword recall difficult when exact titles or terms are forgotten.
- **Dense-Only Retrieval Failure:** Generic vector databases often fail to retrieve exact programming function names, acronyms, or specific technical terms.
- **Hallucination Risk:** Standard LLM chats hallucinate details without direct citations back to the source notes.
- **Privacy & NDA Protection:** Personal and client-sensitive research must remain strictly local on the user's workstation without cloud indexing.

## 3. Proposed Solution
- **Heading-Aware Parsing:** Ingests Markdown preserving frontmatter, `#tags`, wikilinks (`[[Note]]`), and heading hierarchy.
- **Hybrid Retrieval (BM25 + Chroma):** Merges exact keyword matching and semantic embeddings using Reciprocal Rank Fusion (RRF).
- **Cross-Encoder Re-ranking:** Re-scores top passages using `BAAI/bge-reranker-base` to guarantee high precision context.
- **Verifiable Citations:** Returns inline citations `[1]` with exact note titles, heading paths, and source line numbers.
- **Graph Awareness:** Surfaces 1-hop outgoing links and backlinks for retrieved notes.

