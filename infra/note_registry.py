"""SQLite registry of indexed notes, their tags, and their wikilinks.

The registry is the commit point of indexing: a note's SHA-256 is written here
only after its chunks are stored, so an interrupted sync is retried next time.
It also owns metadata filtering (tags / folder) and Obsidian-style wikilink
resolution used to surface 1-hop "related notes".
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from infra.markdown_parser import WikiLink, normalize_tag
from infra.sqlite_utils import connect

__all__ = [
    "NoteRecord",
    "NoteRegistry",
    "RelatedNote",
    "make_note_id",
    "normalize_link_target",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    note_id     TEXT PRIMARY KEY,
    rel_path    TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    stem        TEXT NOT NULL,
    folder      TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    aliases     TEXT NOT NULL,
    chunk_count INTEGER NOT NULL,
    indexed_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS note_tags (
    note_id TEXT NOT NULL REFERENCES notes(note_id) ON DELETE CASCADE,
    tag     TEXT NOT NULL,
    PRIMARY KEY (note_id, tag)
);
CREATE TABLE IF NOT EXISTS links (
    source_id  TEXT NOT NULL REFERENCES notes(note_id) ON DELETE CASCADE,
    target     TEXT NOT NULL,
    target_key TEXT NOT NULL,
    heading    TEXT,
    is_embed   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_id);
CREATE INDEX IF NOT EXISTS idx_links_target_key ON links(target_key);
CREATE INDEX IF NOT EXISTS idx_note_tags_tag ON note_tags(tag);
"""


def make_note_id(rel_path: str) -> str:
    """Derive a stable 16-hex-character id from a vault-relative POSIX path."""
    return hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:16]


def normalize_link_target(target: str) -> str:
    """Normalize a wikilink target for case-insensitive matching."""
    key = target.strip().replace("\\", "/").lstrip("./").lower()
    return key[:-3] if key.endswith(".md") else key


@dataclass(frozen=True)
class NoteRecord:
    """A note as stored in the registry."""

    note_id: str
    rel_path: str
    title: str
    folder: str
    sha256: str
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    chunk_count: int = 0
    indexed_at: str = ""

    @property
    def stem(self) -> str:
        """Filename without folder or ``.md`` extension."""
        return PurePosixPath(self.rel_path).stem

    @classmethod
    def build(cls, rel_path: str, title: str, sha256: str, tags: list[str],
              aliases: list[str], chunk_count: int) -> "NoteRecord":
        """Create a record with derived id, folder, and timestamp."""
        parent = PurePosixPath(rel_path).parent.as_posix()
        return cls(
            note_id=make_note_id(rel_path),
            rel_path=rel_path,
            title=title,
            folder="" if parent == "." else parent,
            sha256=sha256,
            tags=tags,
            aliases=aliases,
            chunk_count=chunk_count,
            indexed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )


@dataclass(frozen=True)
class RelatedNote:
    """A note connected to another by a wikilink (outgoing or backlink)."""

    note_id: str | None
    title: str
    rel_path: str | None
    relation: str

    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return {"note_id": self.note_id, "title": self.title,
                "rel_path": self.rel_path, "relation": self.relation}


class NoteRegistry:
    """CRUD, filtering, and wikilink resolution over the notes database."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        with connect(self._db_path) as connection:
            connection.executescript(_SCHEMA)

    # ----- writes -----------------------------------------------------------

    def upsert_note(self, record: NoteRecord, links: list[WikiLink]) -> None:
        """Insert or replace a note together with its tags and links."""
        with connect(self._db_path) as connection:
            connection.execute("DELETE FROM notes WHERE note_id = ?", (record.note_id,))
            connection.execute(
                "INSERT INTO notes (note_id, rel_path, title, stem, folder, sha256, aliases,"
                " chunk_count, indexed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record.note_id, record.rel_path, record.title, record.stem.lower(),
                 record.folder, record.sha256, json.dumps(record.aliases),
                 record.chunk_count, record.indexed_at),
            )
            connection.executemany(
                "INSERT OR IGNORE INTO note_tags (note_id, tag) VALUES (?, ?)",
                [(record.note_id, normalize_tag(tag)) for tag in record.tags],
            )
            connection.executemany(
                "INSERT INTO links (source_id, target, target_key, heading, is_embed)"
                " VALUES (?, ?, ?, ?, ?)",
                [(record.note_id, link.target, normalize_link_target(link.target),
                  link.heading, int(link.is_embed)) for link in links],
            )

    def delete_note(self, note_id: str) -> None:
        """Remove a note; tags and outgoing links cascade."""
        with connect(self._db_path) as connection:
            connection.execute("DELETE FROM notes WHERE note_id = ?", (note_id,))

    def reset(self) -> None:
        """Delete every note, tag, and link."""
        with connect(self._db_path) as connection:
            connection.execute("DELETE FROM notes")

    # ----- reads ------------------------------------------------------------

    def _row_to_record(self, row: sqlite3.Row, tags: list[str]) -> NoteRecord:
        return NoteRecord(
            note_id=row["note_id"], rel_path=row["rel_path"], title=row["title"],
            folder=row["folder"], sha256=row["sha256"], tags=tags,
            aliases=json.loads(row["aliases"]), chunk_count=row["chunk_count"],
            indexed_at=row["indexed_at"],
        )

    def _tags_by_note(self, connection: sqlite3.Connection) -> dict[str, list[str]]:
        tags: dict[str, list[str]] = {}
        for row in connection.execute("SELECT note_id, tag FROM note_tags ORDER BY tag"):
            tags.setdefault(row["note_id"], []).append(row["tag"])
        return tags

    def list_notes(self) -> list[NoteRecord]:
        """Return every registered note ordered by path."""
        with connect(self._db_path) as connection:
            tags = self._tags_by_note(connection)
            rows = connection.execute("SELECT * FROM notes ORDER BY rel_path").fetchall()
        return [self._row_to_record(row, tags.get(row["note_id"], [])) for row in rows]

    def get_note(self, note_id: str) -> NoteRecord | None:
        """Return a single note or ``None``."""
        with connect(self._db_path) as connection:
            row = connection.execute("SELECT * FROM notes WHERE note_id = ?", (note_id,)).fetchone()
            tags = [r["tag"] for r in connection.execute(
                "SELECT tag FROM note_tags WHERE note_id = ? ORDER BY tag", (note_id,))]
        return self._row_to_record(row, tags) if row else None

    def stats(self) -> dict:
        """Aggregate counts plus available tags/folders for UI filters."""
        with connect(self._db_path) as connection:
            notes = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(chunk_count), 0), MAX(indexed_at) FROM notes"
            ).fetchone()
            tags = connection.execute(
                "SELECT tag, COUNT(*) AS n FROM note_tags GROUP BY tag ORDER BY n DESC, tag"
            ).fetchall()
            folders = connection.execute(
                "SELECT DISTINCT folder FROM notes WHERE folder != '' ORDER BY folder"
            ).fetchall()
        return {
            "notes": notes[0],
            "chunks": notes[1],
            "last_indexed_at": notes[2],
            "tags": [{"tag": row["tag"], "count": row["n"]} for row in tags],
            "folders": [row["folder"] for row in folders],
        }

    def filter_note_ids(self, tags: list[str] | None, folder: str | None) -> set[str] | None:
        """Return note ids matching ANY of ``tags`` within ``folder`` (and subfolders).

        Returns ``None`` when no filter is requested so callers can skip filtering.
        """
        clean_tags = [normalize_tag(tag) for tag in (tags or []) if normalize_tag(tag)]
        clean_folder = (folder or "").strip().strip("/")
        if not clean_tags and not clean_folder:
            return None

        query = "SELECT DISTINCT n.note_id FROM notes n"
        clauses: list[str] = []
        params: list[str] = []
        if clean_tags:
            query += " JOIN note_tags t ON t.note_id = n.note_id"
            clauses.append(f"t.tag IN ({', '.join('?' for _ in clean_tags)})")
            params.extend(clean_tags)
        if clean_folder:
            clauses.append("(n.folder = ? OR substr(n.folder, 1, length(?) + 1) = ? || '/')")
            params.extend([clean_folder, clean_folder, clean_folder])
        query += " WHERE " + " AND ".join(clauses)

        with connect(self._db_path) as connection:
            return {row["note_id"] for row in connection.execute(query, params)}

    # ----- wikilinks --------------------------------------------------------

    def _candidates(self, connection: sqlite3.Connection, key: str) -> list[sqlite3.Row]:
        """Notes a normalized target could refer to (stem, alias, or path suffix)."""
        rows = connection.execute("SELECT note_id, rel_path, title, aliases, stem FROM notes").fetchall()
        matches = []
        for row in rows:
            path_key = normalize_link_target(row["rel_path"])
            aliases = [alias.lower() for alias in json.loads(row["aliases"])]
            if "/" in key:
                hit = path_key == key or path_key.endswith("/" + key)
            else:
                hit = row["stem"] == key or key in aliases
            if hit:
                matches.append(row)
        return sorted(matches, key=lambda r: (len(r["rel_path"]), r["rel_path"]))

    def resolve(self, target: str) -> NoteRecord | None:
        """Resolve a wikilink target like Obsidian: shortest matching path wins."""
        key = normalize_link_target(target)
        if not key:
            return None
        with connect(self._db_path) as connection:
            candidates = self._candidates(connection, key)
        return self.get_note(candidates[0]["note_id"]) if candidates else None

    def related(self, note_id: str) -> list[RelatedNote]:
        """Return 1-hop neighbours: outgoing links (incl. unresolved) and backlinks."""
        note = self.get_note(note_id)
        if note is None:
            return []
        with connect(self._db_path) as connection:
            outgoing = connection.execute(
                "SELECT DISTINCT target FROM links WHERE source_id = ?", (note_id,)
            ).fetchall()
            keys = {note.stem.lower(), *(alias.lower() for alias in note.aliases)}
            path_key = normalize_link_target(note.rel_path)
            incoming = connection.execute(
                "SELECT DISTINCT l.source_id, l.target FROM links l"
                f" WHERE l.target_key IN ({', '.join('?' for _ in keys)})"
                " OR l.target_key = ? OR ? LIKE '%/' || l.target_key",
                [*keys, path_key, path_key],
            ).fetchall()
        return self._dedupe(note_id, outgoing, incoming)

    def _dedupe(self, note_id: str, outgoing: list, incoming: list) -> list[RelatedNote]:
        """Resolve raw link rows into unique :class:`RelatedNote` objects."""
        related: dict[str, RelatedNote] = {}
        for row in outgoing:
            target = self.resolve(row["target"])
            if target is None:
                related.setdefault(f"unresolved:{row['target'].lower()}",
                                   RelatedNote(None, row["target"], None, "unresolved"))
            elif target.note_id != note_id:
                related.setdefault(target.note_id,
                                   RelatedNote(target.note_id, target.title, target.rel_path, "links_to"))
        for row in incoming:
            resolved = self.resolve(row["target"])
            source = self.get_note(row["source_id"])
            if resolved and resolved.note_id == note_id and source and source.note_id != note_id:
                existing = related.get(source.note_id)
                relation = "mutual" if existing and existing.relation == "links_to" else "linked_from"
                related[source.note_id] = RelatedNote(source.note_id, source.title, source.rel_path, relation)
        return sorted(related.values(), key=lambda r: (r.relation == "unresolved", r.title.lower()))

