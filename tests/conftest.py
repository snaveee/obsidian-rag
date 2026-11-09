"""Pytest fixtures for obsidian-rag.

Provides temporary isolated database paths, mock embedding clients,
sample parsed notes, and a configured FastAPI TestClient.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from infra.embeddings import EmbeddingClient
from infra.keyword_index import KeywordStore
from infra.note_registry import NoteRegistry
from infra.vector_store import VectorStore


class MockEmbeddingClient(EmbeddingClient):
    """Deterministic mock embedding client that produces fixed 3-dim vectors."""

    def __init__(self) -> None:
        super().__init__(ollama_url="http://mock-ollama:11434", model="mock-embed")

    def embed_texts(self, texts, is_query: bool = False):
        res = []
        for t in texts:
            # Simple deterministic pseudo-vector based on length and hash
            val = float(len(t) % 100) / 100.0
            res.append([val, 1.0 - val, 0.5])
        return res

    def embed_query(self, query: str):
        return self.embed_texts([query], is_query=True)[0]


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Temporary workspace directory cleaned up after test."""
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mock_embedder() -> MockEmbeddingClient:
    return MockEmbeddingClient()


@pytest.fixture
def test_registry(temp_dir: Path) -> NoteRegistry:
    return NoteRegistry(temp_dir / "test_registry.sqlite3")


@pytest.fixture
def test_keyword_store(temp_dir: Path) -> KeywordStore:
    return KeywordStore(temp_dir / "test_fts.sqlite3")


@pytest.fixture
def test_vector_store(temp_dir: Path) -> VectorStore:
    return VectorStore(temp_dir / "test_chroma", collection_name="test_col")


@pytest.fixture
def sample_vault_path() -> Path:
    p = Path(__file__).resolve().parent.parent / "sample_vault"
    return p


@pytest.fixture
def api_client(temp_dir: Path, monkeypatch) -> Generator[TestClient, None, None]:
    """TestClient wired to isolated temporary databases."""
    monkeypatch.setenv("API_KEY", "test-secret-key")
    monkeypatch.setenv("ORAG_DATA_DIR", str(temp_dir / "data"))
    monkeypatch.setenv("ORAG_VAULT_PATH", str(Path(__file__).resolve().parent.parent / "sample_vault"))

    from infra import main
    # Point main stores to temporary dir
    main.settings = main.load_settings()
    main.registry = NoteRegistry(temp_dir / "api_reg.sqlite3")
    main.keyword_store = KeywordStore(temp_dir / "api_fts.sqlite3")
    main.vector_store = VectorStore(temp_dir / "api_chroma", collection_name="api_test")
    main.history_store = main.HistoryStore(temp_dir / "api_hist.sqlite3")
    main.embedding_client = MockEmbeddingClient()

    main.search_engine.registry = main.registry
    main.search_engine.keyword_store = main.keyword_store
    main.search_engine.vector_store = main.vector_store
    main.search_engine.embedding_client = main.embedding_client

    main.indexer.registry = main.registry
    main.indexer.keyword_store = main.keyword_store
    main.indexer.vector_store = main.vector_store
    main.indexer.embedding_client = main.embedding_client

    client = TestClient(main.app)
    yield client

