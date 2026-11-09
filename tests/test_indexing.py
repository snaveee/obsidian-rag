"""Unit tests for incremental vault indexing and conflict locking."""

import threading
from pathlib import Path

import pytest

from infra.indexing import IndexConflictError, VaultIndexer
from infra.keyword_index import KeywordStore
from infra.note_registry import NoteRegistry
from infra.vector_store import VectorStore


def test_vault_indexer_incremental_add_update_delete(
    temp_dir: Path,
    test_registry: NoteRegistry,
    test_keyword_store: KeywordStore,
    test_vector_store: VectorStore,
    mock_embedder,
):
    vault = temp_dir / "vault"
    vault.mkdir()

    file1 = vault / "note1.md"
    file1.write_text("# Note 1\nInitial content.", encoding="utf-8")

    indexer = VaultIndexer(
        vault_path=vault,
        registry=test_registry,
        keyword_store=test_keyword_store,
        vector_store=test_vector_store,
        embedding_client=mock_embedder,
    )

    # 1. First sync -> added: 1
    rep1 = indexer.sync(full_reindex=False)
    assert rep1.added == 1
    assert rep1.skipped == 0
    assert rep1.total_notes == 1

    # 2. Second sync with no changes -> skipped: 1
    rep2 = indexer.sync(full_reindex=False)
    assert rep2.added == 0
    assert rep2.skipped == 1

    # 3. Modify note1 -> updated: 1
    file1.write_text("# Note 1\nModified content.", encoding="utf-8")
    rep3 = indexer.sync(full_reindex=False)
    assert rep3.updated == 1

    # 4. Delete note1 -> deleted: 1
    file1.unlink()
    rep4 = indexer.sync(full_reindex=False)
    assert rep4.deleted == 1
    assert rep4.total_notes == 0


def test_vault_indexer_lock_prevents_concurrency(
    temp_dir: Path,
    test_registry: NoteRegistry,
    test_keyword_store: KeywordStore,
    test_vector_store: VectorStore,
    mock_embedder,
):
    indexer = VaultIndexer(
        vault_path=temp_dir,
        registry=test_registry,
        keyword_store=test_keyword_store,
        vector_store=test_vector_store,
        embedding_client=mock_embedder,
    )

    # Manually hold lock to simulate running indexing task
    assert indexer._lock.acquire(blocking=False)
    try:
        with pytest.raises(IndexConflictError):
            indexer.sync(full_reindex=False)
    finally:
        indexer._lock.release()

