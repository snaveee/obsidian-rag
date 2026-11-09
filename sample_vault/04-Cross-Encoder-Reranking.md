---
title: Cross-Encoder Re-ranking with BGE
tags: [ml, reranking, bge]
aliases: [BGE Reranker, Cross-Encoder]
---

# Cross-Encoder Re-ranking with BGE

While bi-encoders generate separate embeddings for queries and documents, cross-encoders process the concatenated pair $(Query, Passage)$ simultaneously through all transformer layers.

## Comparison: Bi-Encoder vs. Cross-Encoder

- **Bi-Encoder (Vector Store)**: $Sim(E(Q), E(D))$ allows fast approximate nearest neighbor search over millions of documents via ChromaDB ([[02-Vector-Databases]]), but lacks fine-grained token cross-attention.
- **Cross-Encoder**: Computes all-to-all cross-attention across all tokens in both query and passage. It produces significantly higher precision at the cost of higher latency.

## Model Selection

We utilize `BAAI/bge-reranker-base`. Candidates filtered via [[Reciprocal-Rank-Fusion]] are scored and sorted, discarding low-relevance noise before context is sent to the LLM. High precision retrieval is essential for automated evaluation pipelines like [[06-RLHF-Evaluation-Rubrics]].

