"""ChromaDB vector store adapter for dense semantic similarity search.

Stores embedded note chunks with cosine distance space and provides
metadata filtering by ``note_id``.
"""

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from infra.chunking import Chunk

__all__ = ["VectorSearchResult", "VectorStore"]

logger = logging.getLogger(__name__)


class VectorSearchResult:
    """A scored chunk match from dense vector search."""

    def __init__(self, chunk_id: str, note_id: str, score: float, metadata: dict[str, Any]) -> None:
        self.chunk_id = chunk_id
        self.note_id = note_id
        self.score = score  # Cosine similarity in [0, 1] (1 - distance)
        self.metadata = metadata

    def __repr__(self) -> str:
        return f"<VectorSearchResult chunk_id={self.chunk_id} score={self.score:.4f}>"


class VectorStore:
    """Wrapper around ChromaDB PersistentClient for note chunk vectors."""

    def __init__(self, persist_dir: Path, collection_name: str = "obsidian_notes") -> None:
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        note_title: str,
    ) -> None:
        """Upsert a list of chunks and their embedding vectors into ChromaDB."""
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings length mismatch.")

        ids = [c.chunk_id for c in chunks]
        docs = [c.text for c in chunks]
        metadatas = [
            {
                "note_id": c.note_id,
                "chunk_id": c.chunk_id,
                "chunk_index": c.chunk_index,
                "title": note_title,
                "heading_path": c.heading_path,
                "line_start": c.line_start,
                "line_end": c.line_end,
            }
            for c in chunks
        ]

        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=docs,
        )

    def delete_note_chunks(self, note_id: str) -> None:
        """Delete all chunks belonging to a given note_id."""
        try:
            self._collection.delete(where={"note_id": note_id})
        except Exception as exc:
            logger.debug("Failed deleting chunks for note %s: %s", note_id, exc)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        allowed_note_ids: set[str] | None = None,
    ) -> list[VectorSearchResult]:
        """Perform dense vector search with optional note_id pre-filtering."""
        if top_k <= 0 or self._collection.count() == 0:
            return []

        where_clause: dict[str, Any] | None = None
        if allowed_note_ids is not None:
            if not allowed_note_ids:
                return []
            if len(allowed_note_ids) == 1:
                where_clause = {"note_id": next(iter(allowed_note_ids))}
            else:
                where_clause = {"note_id": {"$in": sorted(allowed_note_ids)}}

        n_results = min(top_k, self._collection.count())
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": n_results,
            "include": ["metadatas", "distances"],
        }
        if where_clause:
            query_kwargs["where"] = where_clause

        try:
            res = self._collection.query(**query_kwargs)
        except Exception as exc:
            logger.error("Chroma query failed: %s", exc)
            return []

        ids_list = res.get("ids", [[]])[0]
        dists_list = res.get("distances", [[]])[0]
        metas_list = res.get("metadatas", [[]])[0]

        results: list[VectorSearchResult] = []
        for cid, dist, meta in zip(ids_list, dists_list, metas_list):
            meta = meta or {}
            # Cosine distance to similarity: 1 - dist
            sim = max(0.0, min(1.0, 1.0 - float(dist)))
            results.append(
                VectorSearchResult(
                    chunk_id=cid,
                    note_id=str(meta.get("note_id", "")),
                    score=sim,
                    metadata=meta,
                )
            )

        return results

    def count(self) -> int:
        """Total number of vectors indexed in the collection."""
        return self._collection.count()

    def reset(self) -> None:
        """Clear all vectors from the collection."""
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )

