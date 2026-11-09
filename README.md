# obsidian-rag 🧠

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-VectorStore-orange.svg)](https://www.trychroma.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An offline-capable, privacy-first **Hybrid Retrieval-Augmented Generation (RAG)** copilot built specifically for **Obsidian knowledge vaults**, developer logs, and technical second-brains.

Combines sparse **BM25 text search** (SQLite FTS5) with **dense semantic embeddings** (ChromaDB), merges them using **Reciprocal Rank Fusion (RRF)**, re-ranks top passages with a **Cross-Encoder transformer** (`BAAI/bge-reranker-base`), and synthesizes grounded answers with strict, verifiable source citations using local LLMs (Ollama).

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Ingestion ["1. Vault Ingestion & Parsing"]
        V[Obsidian Vault .md Files] --> L[vault_loader: SHA-256 + path escape guard]
        L --> P[markdown_parser: frontmatter, #tags, [[wikilinks]]]
        P --> C[chunking: heading-aware sliding window + breadcrumbs]
        P --> R[(note_registry SQLite: notes + 1-hop graph)]
    end

    subgraph Storage ["2. Dual Indexing Layer"]
        C --> E[embeddings: Ollama nomic-embed-text]
        E --> VS[(ChromaDB Dense Vectors)]
        C --> FTS[(SQLite FTS5 BM25 Sparse Index)]
    end

    subgraph Retrieval ["3. Multi-Stage Retrieval & Generation"]
        Q[User Query] --> H[Hybrid Search Engine]
        VS --> H
        FTS --> H
        H --> RRF[Reciprocal Rank Fusion - RRF k=60]
        RRF --> CE[BAAI/bge-reranker-base Cross-Encoder]
        CE --> GEN[Grounded Answer Generator]
        GEN --> UI[Streamlit Interactive Dashboard]
        GEN --> HIST[(SQLite Search History & Deduplication)]
    end
```

---

## ⚡ Key Highlights & Engineering Features

- **Heading-Aware Semantic Chunking**: Respects Markdown section boundaries and prepends hierarchical breadcrumbs (`Title > Section > Subsection`) to every chunk, ensuring context is preserved even when snippets are retrieved independently.
- **Code Block Isolation**: Fenced code blocks are masked before extracting metadata, preventing `#comments` and mock `[[links]]` inside code from corrupting the note index.
- **Multi-Stage Hybrid Search**: Combines the precision of exact keyword matching (BM25) with high-recall semantic vector search (ChromaDB) via Reciprocal Rank Fusion ($k=60$).
- **Cross-Encoder Re-ranking**: Integrates `BAAI/bge-reranker-base` for joint token cross-attention, boosting Hit@1 and MRR across complex technical queries.
- **Graceful Degradation**: If Ollama or the GPU is offline, the retrieval engine automatically degrades to BM25 keyword-only mode without crashing.
- **Strict Grounding & Prompt Defense**: All retrieved passages are isolated inside untrusted context wrappers. The model is constrained to answer solely from context with explicit numerical citations `[1]`, falling back to a sentinel when context is insufficient.
- **1-Hop Wikilink Graph Traversal**: Discovers outgoing links, backlinks, and mutual connections for cited notes.
- **Telemetry & History**: Search queries are logged to SQLite with intelligent `distinct` deduplication, preserving the latest timestamp for one-click query replay.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+
- (Optional) [Ollama](https://ollama.com/) running locally with models:
  ```bash
  ollama pull llama3.2:3b
  ollama pull nomic-embed-text
  ```

### 2. Installation
```bash
git clone https://github.com/snaveee/obsidian-rag.git
cd obsidian-rag
pip install -r core/dependencies.txt
```

### 3. Configuration
Copy the configuration template:
```bash
copy .env.example .env
```

By default, `.env` points to the included `sample_vault/` directory containing 8 realistic technical notes. To point to your own Obsidian vault, simply edit:
```env
ORAG_VAULT_PATH=C:/Users/your-username/Obsidian Vault/VAULT
```

### 4. Running the Application
Launch the FastAPI backend and Streamlit dashboard:

**Terminal 1 (Backend API):**
```bash
fastapi.bat
# or: uvicorn infra.main:app --host 127.0.0.1 --port 8001 --reload
```

**Terminal 2 (Streamlit UI):**
```bash
run.bat
# or: streamlit run streamlit_app.py --server.port 8501
```

Open your browser at `http://localhost:8501`, click **Sync Vault** in the sidebar, and start asking questions!

---

## 📡 API Reference

All backend endpoints (except public `/`) require authentication via the `X-API-Key` HTTP header.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Public health check, total indexed notes/chunks, and active model names. |
| `POST` | `/index` | Trigger incremental SHA-256 sync or full re-index (`{"full_reindex": false}`). |
| `POST` | `/search` | Retrieve ranked candidates via hybrid search without LLM generation. |
| `POST` | `/ask` | Execute full grounded RAG query: returns answer, citations, sources, and related notes. |
| `GET` | `/notes/{id}/related` | Return 1-hop outgoing links and backlinks for a specific note. |
| `GET` | `/history` | Fetch search history log with optional distinct query deduplication. |

---

## 🧪 Testing & Benchmarking

### Automated Test Suite
Run the comprehensive offline test suite (mocking external dependencies):
```bash
pytest -v
```

### Retrieval Quality Benchmark
Evaluate Hit@1, Hit@3, MRR, and execution latency across different search configurations:
```bash
python scripts/benchmark_retrieval.py
```

Sample output:
```text
=================================================================
 obsidian-rag Retrieval & Latency Benchmark
 Vault Path: sample_vault
=================================================================
--- BM25 Keyword Only ---
 Hit@1: 4/5 (80.0%)
 Hit@3: 5/5 (100.0%)
 MRR:   0.8667
 Latency (avg): 1.84ms

--- Hybrid RRF + Rerank ---
 Hit@1: 5/5 (100.0%)
 Hit@3: 5/5 (100.0%)
 MRR:   1.0000
 Latency (avg): 24.31ms
=================================================================
```

---

## 📂 Repository Structure

```text
obsidian-rag/
├── core/                       # Architectural context, requirements, and file definitions
│   ├── PROJECT-CONTEXT.md
│   ├── MUST-HAVES.md
│   ├── FILE-DEFINITIONS.md
│   └── dependencies.txt
├── documentation/              # Reverse-chronological master changelog
│   └── MASTER-CHANGES.md
├── infra/                      # Core pipeline modules
│   ├── config.py               # Centralized immutable settings
│   ├── auth.py                 # Constant-time API key verification
│   ├── sqlite_utils.py         # Transactional SQLite context manager
│   ├── vault_loader.py         # Path-safe vault file scanner
│   ├── markdown_parser.py      # Frontmatter, #tag, and wikilink parser
│   ├── chunking.py             # Heading-aware sliding window chunker
│   ├── note_registry.py        # SQLite metadata registry and graph links
│   ├── embeddings.py           # Ollama embedding client
│   ├── vector_store.py         # ChromaDB cosine distance store
│   ├── keyword_index.py        # SQLite FTS5 BM25 search
│   ├── reranking.py            # BGE Cross-Encoder re-ranker
│   ├── hybrid_search.py        # Reciprocal Rank Fusion hybrid engine
│   ├── indexing.py             # Incremental SHA-256 sync coordinator
│   ├── generation.py           # Grounded answer synthesis & citation parser
│   ├── history_store.py        # Search history telemetry
│   └── main.py                 # FastAPI backend entrypoint
├── sample_vault/               # 8 interlinked demo markdown notes
├── scripts/                    # Benchmarking scripts
│   └── benchmark_retrieval.py
├── tests/                      # Full test suite (AppTest, offline unit & integration)
├── streamlit_app.py            # Streamlit dashboard
├── .env.example                # Configuration template
├── run.bat / fastapi.bat       # Windows launchers
└── README.md                   # This file
```

---

## 🔒 Security & Privacy

- **Zero Cloud Egress**: Embeddings, vector searches, and LLM generations run 100% locally on your machine.
- **Data Boundary**: `.gitignore` strictly ignores `.env` and `data/` directories, ensuring personal notes and generated databases are never committed to version control.
- **Path Traversal Protection**: Note loader strictly verifies that every discovered file resides within the vault directory boundary.

