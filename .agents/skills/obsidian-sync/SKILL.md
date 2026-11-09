---
name: obsidian-sync
description: >-
  Synchronize obsidian-rag core architectural documentation and master developer logs into the existing Obsidian Vault hierarchy (VAULT/OBSIDIAN-RAG/CORE and VAULT/OBSIDIAN-RAG/DOCUMENTATION).
  Excludes core/dependencies.txt, formats markdown files with Obsidian [[wikilinks]], maintains folder-level index notes (CORE.md, DOCUMENTATION.md, OBSIDIAN-RAG.md), and preserves the parent [[VAULT]] hierarchy.
  Triggers: "sync obsidian", "update obsidian vault", "sync vault", "obsidian graph", "update obsidian", "export to obsidian".
---

# Obsidian Vault Synchronization (`obsidian-sync`)

This skill synchronizes the internal architectural documentation and development logs from the `obsidian-rag` project into your local Obsidian Vault, integrating your code documentation into your personal knowledge graph.

---

## 1. Target Vault Hierarchy

```text
VAULT/
  ├── VAULT.md             (Root Hub note)
  └── OBSIDIAN-RAG/
      ├── OBSIDIAN-RAG.md  (Project Hub note -> links up to [[VAULT]])
      ├── CORE/
      │   ├── CORE.md      (Folder Hub note -> links up to [[OBSIDIAN-RAG]])
      │   ├── PROJECT-CONTEXT.md
      │   ├── MUST-HAVES.md
      │   └── FILE-DEFINITIONS.md
      └── DOCUMENTATION/
          ├── DOCUMENTATION.md (Folder Hub note -> links up to [[OBSIDIAN-RAG]])
          └── MASTER-CHANGES.md
```

---

## 2. Execution

To trigger the synchronization script directly:

```powershell
python .agents/skills/obsidian-sync/scripts/sync_vault.py
```
