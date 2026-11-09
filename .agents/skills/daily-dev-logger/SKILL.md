---
name: daily-dev-logger
description: >-
  Generate, update, and synchronize standardized, token-dense daily developer documentation from git commits, branches, and diffs for obsidian-rag.
  Directly syncs entries into the master documentation (documentation/MASTER-CHANGES.md) in reverse-chronological order (newest at top),
  synchronizes the living architectural map (core/FILE-DEFINITIONS.md), and mirrors core & documentation files into the Obsidian Vault.
  Triggers: "document today's changes", "update dev log", "document commits", "update changelog", "devlog", "sync documentation", "update file definitions".
---

# Daily Developer Logger (`daily-dev-logger`)

This skill automates the tracking, semantic analysis, and synchronization of developer progress and architectural changes across the `obsidian-rag` project. It ensures that every commit, feature branch, and bug fix is captured with technical precision, token-dense context, and synchronized into `documentation/MASTER-CHANGES.md` and `core/FILE-DEFINITIONS.md`.

---

## 1. Documentation Structure & Master Log

| Role | Author | Responsibility | Primary Log File |
| :--- | :--- | :--- | :--- |
| **Evans** | `snaveee` | Lead Developer & Core Architecture | [`documentation/MASTER-CHANGES.md`](file:///c:/Users/snaaa/projects/obsidian-rag/documentation/MASTER-CHANGES.md) |
| **Architectural Map** | *System* | Living File, Symbol & Test Dictionary | [`core/FILE-DEFINITIONS.md`](file:///c:/Users/snaaa/projects/obsidian-rag/core/FILE-DEFINITIONS.md) |

---

## 2. Core Operating Rules

1. **Reverse-Chronological Master Sync:**
   - Every entry is inserted at the top of `documentation/MASTER-CHANGES.md` under the appropriate date heading `## [YYYY-MM-DD]`.
2. **Synchronize File Definitions (`core/FILE-DEFINITIONS.md`):**
   - Whenever a commit introduces new files, deletes files, or updates modules, update the catalog and exported symbols in `core/FILE-DEFINITIONS.md`.
3. **Token-Dense & High Technical Detail:**
   - Eliminate fluff. Document exact symbol names, functions, configuration variables, and behavioral changes.
4. **Trigger Obsidian Vault Mirroring:**
   - After updating local documentation, optionally invoke `obsidian-sync` to mirror docs into your vault.
