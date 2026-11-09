"""Unit tests for NoteRegistry: CRUD, filtering, and 1-hop wikilinks."""

from infra.markdown_parser import WikiLink
from infra.note_registry import NoteRecord, NoteRegistry


def test_note_registry_upsert_and_get(test_registry: NoteRegistry):
    rec = NoteRecord.build(
        rel_path="systems/arch.md",
        title="Architecture Guide",
        sha256="abc123sha",
        tags=["architecture", "rag"],
        aliases=["ArchDoc"],
        chunk_count=3,
    )
    links = [
        WikiLink(target="systems/db.md"),
        WikiLink(target="unresolved_note"),
    ]
    test_registry.upsert_note(rec, links)

    fetched = test_registry.get_note(rec.note_id)
    assert fetched is not None
    assert fetched.title == "Architecture Guide"
    assert fetched.folder == "systems"
    assert "rag" in fetched.tags
    assert "ArchDoc" in fetched.aliases


def test_note_registry_filters(test_registry: NoteRegistry):
    r1 = NoteRecord.build("docs/note1.md", "Note 1", "sha1", ["python"], [], 1)
    r2 = NoteRecord.build("docs/note2.md", "Note 2", "sha2", ["rag"], [], 1)
    r3 = NoteRecord.build("personal/note3.md", "Note 3", "sha3", ["python", "rag"], [], 1)

    test_registry.upsert_note(r1, [])
    test_registry.upsert_note(r2, [])
    test_registry.upsert_note(r3, [])

    # Filter by tag
    tag_ids = test_registry.filter_note_ids(tags=["python"], folder=None)
    assert tag_ids == {r1.note_id, r3.note_id}

    # Filter by folder
    folder_ids = test_registry.filter_note_ids(tags=None, folder="docs")
    assert folder_ids == {r1.note_id, r2.note_id}

    # Combined filter
    combo_ids = test_registry.filter_note_ids(tags=["python"], folder="docs")
    assert combo_ids == {r1.note_id}


def test_note_registry_related_links(test_registry: NoteRegistry):
    r_a = NoteRecord.build("note_a.md", "Note A", "sha_a", [], [], 1)
    r_b = NoteRecord.build("note_b.md", "Note B", "sha_b", [], [], 1)

    # A links to B and an unresolved note
    test_registry.upsert_note(r_a, [WikiLink(target="note_b"), WikiLink(target="missing_target")])
    # B links back to A
    test_registry.upsert_note(r_b, [WikiLink(target="note_a")])

    related_a = test_registry.related(r_a.note_id)
    relations = {r.title: r.relation for r in related_a}

    assert relations.get("Note B") == "mutual"
    assert relations.get("missing_target") == "unresolved"

