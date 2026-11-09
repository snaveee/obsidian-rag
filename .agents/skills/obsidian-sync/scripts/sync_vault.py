"""Obsidian Vault Synchronizer for obsidian-rag.

Mirrors obsidian-rag's core architectural documentation and developer logs
into the existing Obsidian Vault hierarchy:
  VAULT/OBSIDIAN-RAG/CORE
  VAULT/OBSIDIAN-RAG/DOCUMENTATION

Excludes dependencies.txt, converts links to [[wikilinks]], maintains folder
index notes:
  - VAULT/OBSIDIAN-RAG/OBSIDIAN-RAG.md
  - VAULT/OBSIDIAN-RAG/CORE/CORE.md
  - VAULT/OBSIDIAN-RAG/DOCUMENTATION/DOCUMENTATION.md
"""

import os
import re
import shutil
from pathlib import Path

VAULT_DEFAULT_PATH = Path("C:/Users/snaaa/Obsidian Vault/VAULT")
WORKSPACE_ROOT = Path("C:/Users/snaaa/projects/obsidian-rag")

EXCLUDE_CORE = {"dependencies.txt"}
REQUIRED_VAULT_STRUCTURE = [
    "OBSIDIAN-RAG",
    "OBSIDIAN-RAG/CORE",
    "OBSIDIAN-RAG/DOCUMENTATION",
]


def resolve_vault_path() -> Path:
    env_path = os.getenv("OBSIDIAN_VAULT_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists() and p.is_dir():
            return p
    return VAULT_DEFAULT_PATH


def convert_links_to_wikilinks(text: str) -> str:
    # Convert [label](file:///...) or [label](path/to/file.md) to [[target|label]] or [[target]]
    pattern = r"\[([^\]]+)\]\((?:file:///[^\)]+|[^\)]+\.md)\)"

    def replacer(m):
        label = m.group(1)
        # If label is already a file path or clean title, use it
        clean_target = Path(label).stem
        if clean_target.lower() == label.lower():
            return f"[[{clean_target}]]"
        return f"[[{clean_target}|{label}]]"

    return re.sub(pattern, replacer, text)


def sync_core(rag_dir: Path) -> list[str]:
    dest_dir = rag_dir / "CORE"
    dest_dir.mkdir(parents=True, exist_ok=True)
    synced = []
    core_src = WORKSPACE_ROOT / "core"
    if not core_src.exists():
        return synced

    for file_path in core_src.glob("*.md"):
        if file_path.name in EXCLUDE_CORE:
            continue
        dest_path = dest_dir / file_path.name
        content = file_path.read_text(encoding="utf-8")
        converted = convert_links_to_wikilinks(content)
        dest_path.write_text(converted, encoding="utf-8")
        synced.append(file_path.name)
    return synced


def sync_documentation(rag_dir: Path) -> list[str]:
    dest_dir = rag_dir / "DOCUMENTATION"
    dest_dir.mkdir(parents=True, exist_ok=True)
    synced = []
    doc_src = WORKSPACE_ROOT / "documentation"
    if not doc_src.exists():
        return synced

    for file_path in doc_src.glob("*.md"):
        dest_path = dest_dir / file_path.name
        content = file_path.read_text(encoding="utf-8")
        converted = convert_links_to_wikilinks(content)
        dest_path.write_text(converted, encoding="utf-8")
        synced.append(file_path.name)
    return synced


def update_folder_indexes(rag_dir: Path) -> list[str]:
    rag_hub = rag_dir / "OBSIDIAN-RAG.md"
    rag_content = """---
title: "obsidian-rag Project Hub"
tags:
  - "hub"
  - "obsidian-rag"
---

# obsidian-rag Knowledge Hub

Up: [[VAULT]]

Personal Second-Brain Knowledge Copilot with hybrid search, RRF, and cross-encoder reranking.

## Navigation
- [[CORE]] - Architectural documentation, system requirements, and file definitions
- [[DOCUMENTATION]] - Master changelogs and timeline
"""
    rag_hub.write_text(rag_content, encoding="utf-8")

    core_hub = rag_dir / "CORE" / "CORE.md"
    core_content = """---
title: "obsidian-rag Core Documentation Hub"
tags:
  - "hub"
  - "core"
---

# Core Architectural Specifications

Up: [[OBSIDIAN-RAG]]

- [[PROJECT-CONTEXT]]
- [[MUST-HAVES]]
- [[FILE-DEFINITIONS]]
"""
    core_hub.write_text(core_content, encoding="utf-8")

    doc_hub = rag_dir / "DOCUMENTATION" / "DOCUMENTATION.md"
    doc_content = """---
title: "obsidian-rag Documentation Hub"
tags:
  - "hub"
  - "documentation"
---

# Developer Logs & Changelog

Up: [[OBSIDIAN-RAG]]

- [[MASTER-CHANGES]]
"""
    doc_hub.write_text(doc_content, encoding="utf-8")

    return [str(rag_hub), str(core_hub), str(doc_hub)]


def main():
    vault_path = resolve_vault_path()
    rag_dir = vault_path / "OBSIDIAN-RAG"
    print(f"Target Vault Directory: {rag_dir}")
    if not vault_path.exists():
        print(f"Vault path does not exist: {vault_path}. Skipping.")
        return

    rag_dir.mkdir(parents=True, exist_ok=True)
    synced_core = sync_core(rag_dir)
    synced_docs = sync_documentation(rag_dir)
    updated_indexes = update_folder_indexes(rag_dir)

    print(f"Synced Core: {synced_core}")
    print(f"Synced Docs: {synced_docs}")
    print(f"Updated Indexes: {len(updated_indexes)}")


if __name__ == "__main__":
    main()
