"""Shared SQLite connection helper.

Every store opens short-lived connections through :func:`connect`, which
guarantees commit-or-rollback semantics and that file handles are always
closed (important on Windows, where open handles lock database files).
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

__all__ = ["connect"]


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection that commits on success and always closes."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
