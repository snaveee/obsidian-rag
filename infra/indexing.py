"""Incremental vault indexing engine.

Coordinates reading notes from the filesystem, parsing, chunking, embedding,
and synchronizing the NoteRegistry, KeywordStore, and VectorStore. Tracks SHA-256
hashes so unchanged notes are skipped. Enforces thread-safe synchronization
via a lock.
"""

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from infra.chunking import chunk_note
from infra.embeddings import EmbeddingClient, EmbeddingUnavailable
from infra.keyword_index import KeywordStore
from infra.markdown_parser import parse_note
from infra.note_registry import NoteRecord, NoteRegistry
from infra.vault_loader import read_note_text, scan_vault
from infra.vector_store import VectorStore

__all__ = ["IndexConflictError", "IndexReport", "VaultIndexer"]

logger = logging.getLogger(__name__)


class IndexConflictError(RuntimeError):
    """Raised when an indexing operation is already in progress."""


@dataclass
class IndexReport:
    """Summary metrics of an indexing run."""

    added: int = 0
    updated: int = 0
    deleted: int = 0
    skipped: int = 0
    total_notes: int = 0
    total_chunks: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": self.added,
            "updated": self.updated,
            "deleted": self.deleted,
            "skipped": self.skipped,
            "total_notes": self.total_notes,
            "total_chunks": self.total_chunks,
            "errors": self.errors,
        }


class VaultIndexer:
    """Coordinates indexing vault files into registry, keyword, and vector stores."""

    def __init__(
        self,
        vault_path: Path,
        registry: NoteRegistry,
        keyword_store: KeywordStore,
        vector_store: VectorStore,
        embedding_client: EmbeddingClient,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
    ) -> None:
        self.vault_path = vault_path
        self.registry = registry
        self.keyword_store = keyword_store
        self.vector_store = vector_store
        self.embedding_client = embedding_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._lock = threading.Lock()

    def sync(self, full_reindex: bool = False) -> IndexReport:
        """Execute synchronization between disk and index databases."""
        if not self._lock.acquire(blocking=False):
            raise IndexConflictError("An indexing job is already running.")

        try:
            return self._run_sync(full_reindex=full_reindex)
        finally:
            self._lock.release()

    def _run_sync(self, full_reindex: bool) -> IndexReport:
        report = IndexReport()

        if full_reindex:
            logger.info("Performing full re-index. Resetting all stores.")
            self.registry.reset()
            self.keyword_store.reset()
            self.vector_store.reset()

        scan = scan_vault(self.vault_path)
        for skip_item in scan.skipped:
            report.errors.append({"file": skip_item["path"], "error": skip_item["reason"]})

        disk_files_by_path = {f.rel_path: f for f in scan.files}
        registered_notes = {n.rel_path: n for n in self.registry.list_notes()}

        # 1. Detect deleted notes
        for rel_path, old_note in registered_notes.items():
            if rel_path not in disk_files_by_path:
                logger.info("Purging deleted note: %s", rel_path)
                self.registry.delete_note(old_note.note_id)
                self.keyword_store.delete_note_chunks(old_note.note_id)
                self.vector_store.delete_note_chunks(old_note.note_id)
                report.deleted += 1

        # 2. Process added or modified notes
        for rel_path, vault_file in disk_files_by_path.items():
            old_record = registered_notes.get(rel_path)
            if old_record and old_record.sha256 == vault_file.sha256 and not full_reindex:
                report.skipped += 1
                continue

            is_update = old_record is not None
            try:
                raw_text = read_note_text(vault_file)
                parsed = parse_note(raw_text, stem=vault_file.abs_path.stem)
                note_id = old_record.note_id if old_record else None
                if not note_id:
                    note_id = NoteRecord.build(
                        rel_path=rel_path,
                        title=parsed.title,
                        sha256=vault_file.sha256,
                        tags=parsed.tags,
                        aliases=parsed.aliases,
                        chunk_count=0,
                    ).note_id

                chunks = chunk_note(
                    note_id=note_id,
                    note=parsed,
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                )

                # Store keyword chunks
                self.keyword_store.upsert_chunks(chunks, note_title=parsed.title)

                # Generate and store dense embeddings
                chunk_texts = [c.text for c in chunks]
                embeddings: list[list[float]] = []
                if chunk_texts:
                    try:
                        embeddings = self.embedding_client.embed_texts(chunk_texts, is_query=False)
                    except EmbeddingUnavailable as emb_err:
                        logger.warning("Embedding skipped for %s (%s)", rel_path, emb_err)
                        # We still keep keyword index working

                if embeddings and len(embeddings) == len(chunks):
                    self.vector_store.upsert_chunks(chunks, embeddings, note_title=parsed.title)

                record = NoteRecord.build(
                    rel_path=rel_path,
                    title=parsed.title,
                    sha256=vault_file.sha256,
                    tags=parsed.tags,
                    aliases=parsed.aliases,
                    chunk_count=len(chunks),
                )
                self.registry.upsert_note(record, parsed.links)

                if is_update:
                    report.updated += 1
                else:
                    report.added += 1

            except Exception as exc:
                logger.error("Failed indexing %s: %s", rel_path, exc, exc_info=True)
                report.errors.append({"file": rel_path, "error": str(exc)})

        stats = self.registry.stats()
        report.total_notes = stats["notes"]
        report.total_chunks = stats["chunks"]
        return report

