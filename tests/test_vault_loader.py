"""Unit tests for vault scanning and filesystem security guards."""

from pathlib import Path

import pytest

from infra.vault_loader import (
    MAX_NOTE_BYTES,
    VaultNotFoundError,
    read_note_text,
    scan_vault,
)


def test_scan_vault_nonexistent(temp_dir: Path):
    with pytest.raises(VaultNotFoundError):
        scan_vault(temp_dir / "does_not_exist")


def test_scan_vault_skips_hidden_and_obsidian(temp_dir: Path):
    # Setup folders
    (temp_dir / ".obsidian").mkdir()
    (temp_dir / ".obsidian" / "config.md").write_text("hidden", encoding="utf-8")

    (temp_dir / ".trash").mkdir()
    (temp_dir / ".trash" / "deleted.md").write_text("trashed", encoding="utf-8")

    (temp_dir / "docs").mkdir()
    (temp_dir / "docs" / "valid.md").write_text("# Valid Note", encoding="utf-8")
    (temp_dir / "root_note.md").write_text("# Root Note", encoding="utf-8")

    scan = scan_vault(temp_dir)
    rel_paths = [f.rel_path for f in scan.files]

    assert "docs/valid.md" in rel_paths
    assert "root_note.md" in rel_paths
    assert not any(".obsidian" in p for p in rel_paths)
    assert not any(".trash" in p for p in rel_paths)


def test_scan_vault_size_cap(temp_dir: Path):
    huge = temp_dir / "huge.md"
    # Write empty file and mock large size
    huge.write_bytes(b"a" * (MAX_NOTE_BYTES + 1024))

    scan = scan_vault(temp_dir)
    assert len(scan.files) == 0
    assert len(scan.skipped) == 1
    assert "larger than" in scan.skipped[0]["reason"]


def test_read_note_text_strips_bom(temp_dir: Path):
    bom_file = temp_dir / "bom.md"
    bom_file.write_bytes(b"\xef\xbb\xbf# Title With BOM\nContent")
    scan = scan_vault(temp_dir)
    assert len(scan.files) == 1

    text = read_note_text(scan.files[0])
    assert text.startswith("# Title With BOM")
    assert not text.startswith("\ufeff")

