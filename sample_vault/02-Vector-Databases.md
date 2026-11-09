---
title: Vector Databases & Dense Embeddings
tags: [vector-search, embeddings, chroma]
aliases: [Vector DB, Chroma Notes]
---

# Vector Databases & Dense Embeddings

Vector databases enable semantic similarity search across dense embedding representations.

## ChromaDB Integration

In our architecture, ChromaDB operates in persistent client mode. It indexes high-dimensional vectors produced by embedding models like `nomic-embed-text`.
Cosine distance is configured (`hnsw:space: cosine`), and similarity is derived as:
`similarity = 1.0 - distance`

## Dense Retrieval Limitations

Dense vector search alone suffers from notable blind spots:
- Exact acronyms and function identifiers (e.g., `sqlite3.connect`).
- Domain-specific jargon with low training representation.
- Numerical identifiers or dates.

To overcome these weaknesses, our system connects ChromaDB with keyword search inside [[01-System-Architecture]]. High-scoring vector matches are later passed to [[Cross-Encoder-Reranking]] for precision sorting.

