---
title: Reciprocal Rank Fusion Algorithm
tags: [algorithms, search, rrf]
aliases: [RRF Algorithm, Rank Fusion]
---

# Reciprocal Rank Fusion (RRF)

Reciprocal Rank Fusion is an unsupervised ranking fusion technique that merges ordered candidate lists from disparate retrieval systems without requiring score normalization.

## Formula & Mechanics

For a document $d$ appearing across multiple ranked lists:

$$RRF\_Score(d) = \sum_{m \in M} \frac{1}{k + rank_m(d)}$$

Where:
- $M$ is the set of retrieval modalities (e.g., BM25 and dense vector search).
- $rank_m(d)$ is the 1-based rank position of document $d$ in system $m$.
- $k$ is a smoothing constant, typically set to $60$.

## Why RRF Outperforms Score Normalization

1. **Robust to Outliers**: BM25 scores can scale arbitrarily high based on term frequency, while cosine similarities range strictly between 0 and 1. RRF relies solely on rank order, preventing one retriever from dominating the score.
2. **Zero Training Requirement**: It functions out-of-the-box without requiring supervised weight training.
3. **Seamless Upstream Pipeline**: Fused candidates are subsequently refined via [[Cross-Encoder-Reranking]] as defined in [[01-System-Architecture]].

