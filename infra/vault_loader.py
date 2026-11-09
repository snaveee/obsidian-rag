"""Discover Markdown notes inside an Obsidian vault.

Walks the vault without following symlinked directories, skips Obsidian's
internal folders, rejects files that resolve outside the vault (path escape
via symlinks), and enforces a per-file size cap.
"""

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "MAX_NOTE_BYTES",
    "SKIPPED_DIRS",
    "VaultFile",
    "VaultNotFoundError",
    "VaultScan",
    "read_note_text",
    "scan_vault",
]

MAX_NOTE_BYTES = 2 * 1024 * 1024
SKIPPED_DIRS = frozenset({".obsidian", ".trash", ".git"})


class VaultNotFoundError(FileNotFoundError):
    """Raised when the configured vault path does not exist or is not a folder."""


@dataclass(frozen=True)
class VaultFile:
    """A Markdown note discovered in the vault."""

    rel_path: str
    abs_path: Path
    sha256: str
    size: int


@dataclass
class VaultScan:
    """Result of scanning a vault: eligible notes plus skipped files and reasons."""

    files: list[VaultFile] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)


def _iter_markdown_paths(root: Path):
    """Yield Markdown file paths, pruning hidden and Obsidian-internal folders."""
    for dir_path, dir_names, file_names in os.walk(root, followlinks=False):
        dir_names[:] = sorted(
            name for name in dir_names
            if name not in SKIPPED_DIRS and not name.startswith(".")
        )
        for file_name in sorted(file_names):
            if file_name.lower().endswith(".md"):
                yield Path(dir_path) / file_name


def _skip_reason(path: Path, root: Path) -> str | None:
    """Return why a path must be skipped, or ``None`` if it is eligible."""
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        return "resolves outside the vault"
    if not resolved.is_file():
        return "not a regular file"
    if resolved.stat().st_size > MAX_NOTE_BYTES:
        return f"larger than {MAX_NOTE_BYTES // (1024 * 1024)} MB"
    return None


def scan_vault(vault_path: Path) -> VaultScan:
    """Scan ``vault_path`` and return eligible notes with their SHA-256 hashes."""
    root = vault_path.resolve()
    if not root.is_dir():
        raise VaultNotFoundError(f"Vault folder not found: {vault_path}")

    scan = VaultScan()
    for path in _iter_markdown_paths(root):
        rel_path = path.relative_to(root).as_posix()
        reason = _skip_reason(path, root)
        if reason:
            scan.skipped.append({"path": rel_path, "reason": reason})
            continue
        payload = path.read_bytes()
        scan.files.append(
            VaultFile(
                rel_path=rel_path,
                abs_path=path,
                sha256=hashlib.sha256(payload).hexdigest(),
                size=len(payload),
            )
        )
    return scan


def read_note_text(vault_file: VaultFile) -> str:
    """Read a note as UTF-8 (invalid bytes replaced) without a leading BOM."""
    text = vault_file.abs_path.read_text(encoding="utf-8", errors="replace")
    return text.removeprefix("\ufeff")
