"""Centralized runtime configuration for obsidian-rag.

Loads ``.env`` from the project root regardless of the current working
directory and exposes a single immutable :class:`Settings` object. Every other
module receives its paths and model names from here, so there is exactly one
place where environment variables are read.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

__all__ = ["PROJECT_ROOT", "Settings", "load_settings"]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)


def _resolve_path(raw_value: str) -> Path:
    """Resolve a configured path; relative paths are anchored at the project root."""
    path = Path(raw_value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable, failing loudly on malformed values."""
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer.") from exc


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment variable (true/false, 1/0, yes/no)."""
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings shared by the API, indexer, and scripts."""

    vault_path: Path
    data_dir: Path
    ollama_url: str
    gen_model: str
    embed_model: str
    gen_num_predict: int
    gen_num_ctx: int
    chunk_size: int
    chunk_overlap: int
    rerank_enabled: bool
    reranker_model: str
    collection_name: str

    @property
    def registry_db(self) -> Path:
        """SQLite database holding notes, tags, and wikilinks."""
        return self.data_dir / "registry.sqlite3"

    @property
    def keyword_db(self) -> Path:
        """SQLite database holding chunk metadata and the FTS5 index."""
        return self.data_dir / "fts_index.sqlite3"

    @property
    def history_db(self) -> Path:
        """SQLite database holding the search history log."""
        return self.data_dir / "history.sqlite3"

    @property
    def chroma_dir(self) -> Path:
        """Persistent ChromaDB directory."""
        return self.data_dir / "chroma"


def load_settings() -> Settings:
    """Build :class:`Settings` from the current environment."""
    settings = Settings(
        vault_path=_resolve_path(os.getenv("ORAG_VAULT_PATH", "sample_vault")),
        data_dir=_resolve_path(os.getenv("ORAG_DATA_DIR", "data")),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        gen_model=os.getenv("ORAG_GEN_MODEL", "llama3.2:3b"),
        embed_model=os.getenv("ORAG_EMBED_MODEL", "nomic-embed-text"),
        gen_num_predict=_env_int("ORAG_GEN_NUM_PREDICT", 450),
        gen_num_ctx=_env_int("ORAG_GEN_NUM_CTX", 8192),
        chunk_size=_env_int("ORAG_CHUNK_SIZE", 800),
        chunk_overlap=_env_int("ORAG_CHUNK_OVERLAP", 120),
        rerank_enabled=_env_bool("ORAG_RERANK", True),
        reranker_model=os.getenv("ORAG_RERANKER_MODEL", "BAAI/bge-reranker-base"),
        collection_name=os.getenv("ORAG_CHROMA_COLLECTION", "obsidian_notes"),
    )
    if not 0 <= settings.chunk_overlap < settings.chunk_size:
        raise ValueError("ORAG_CHUNK_OVERLAP must be >= 0 and smaller than ORAG_CHUNK_SIZE.")
    return settings
