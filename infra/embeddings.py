"""Embedding generation via Ollama (or compatible local HTTP endpoints).

Provides batched embedding generation with prompt prefixing suitable for
retrieval models such as ``nomic-embed-text`` (``search_document:`` for stored
chunks, ``search_query:`` for search queries).
"""

import logging
from typing import Sequence

import requests

__all__ = ["EmbeddingClient", "EmbeddingUnavailable", "get_embedding_client"]

logger = logging.getLogger(__name__)


class EmbeddingUnavailable(RuntimeError):
    """Raised when Ollama is unreachable, returns an error, or the model is missing."""


class EmbeddingClient:
    """Client for generating vector embeddings from Ollama."""

    def __init__(self, ollama_url: str, model: str, timeout: float = 30.0) -> None:
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._embed_endpoint = f"{self.ollama_url}/api/embed"
        self._legacy_endpoint = f"{self.ollama_url}/api/embeddings"

    def _prefix_text(self, text: str, is_query: bool) -> str:
        """Add recommended task prefix for models like nomic-embed-text."""
        if "nomic" in self.model.lower():
            prefix = "search_query: " if is_query else "search_document: "
            if not text.startswith(prefix):
                return f"{prefix}{text}"
        return text

    def embed_texts(self, texts: Sequence[str], is_query: bool = False) -> list[list[float]]:
        """Generate embeddings for a list of text strings."""
        if not texts:
            return []

        prepared = [self._prefix_text(t, is_query=is_query) for t in texts]

        # 1. Try modern /api/embed (Ollama >= 0.1.34)
        try:
            resp = requests.post(
                self._embed_endpoint,
                json={"model": self.model, "input": prepared},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                embeddings = data.get("embeddings")
                if embeddings and len(embeddings) == len(prepared):
                    return embeddings
        except Exception as exc:
            logger.debug("Failed /api/embed: %s", exc)

        # 2. Fallback to /api/embeddings (single or older Ollama versions)
        embeddings_list: list[list[float]] = []
        for single_text in prepared:
            try:
                resp = requests.post(
                    self._legacy_endpoint,
                    json={"model": self.model, "prompt": single_text},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    vec = resp.json().get("embedding")
                    if vec:
                        embeddings_list.append(vec)
                        continue
                raise EmbeddingUnavailable(
                    f"Ollama returned HTTP {resp.status_code}: {resp.text}"
                )
            except requests.RequestException as req_err:
                raise EmbeddingUnavailable(
                    f"Could not connect to Ollama at {self.ollama_url}: {req_err}"
                ) from req_err

        return embeddings_list

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        results = self.embed_texts([query], is_query=True)
        if not results:
            raise EmbeddingUnavailable("No embedding returned for query.")
        return results[0]


def get_embedding_client(ollama_url: str, model: str) -> EmbeddingClient:
    """Factory helper to obtain an EmbeddingClient."""
    return EmbeddingClient(ollama_url=ollama_url, model=model)

