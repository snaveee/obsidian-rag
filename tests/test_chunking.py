"""Unit tests for heading-aware sliding-window chunking."""

from infra.chunking import chunk_note
from infra.markdown_parser import parse_note


def test_chunking_heading_breadcrumbs():
    raw = """---
title: System Architecture
---

# Section Alpha
Line one of section alpha.
Line two of section alpha.

## Sub-Section Beta
Line one of beta.
Line two of beta.
"""
    parsed = parse_note(raw, stem="sys_arch")
    chunks = chunk_note(
        note_id="note_123",
        note=parsed,
        chunk_size=500,
        chunk_overlap=50,
    )

    assert len(chunks) == 2
    assert "System Architecture > Section Alpha" in chunks[0].text
    assert "System Architecture > Section Alpha > Sub-Section Beta" in chunks[1].text
    assert chunks[0].heading_path == "Section Alpha"
    assert chunks[1].heading_path == "Section Alpha > Sub-Section Beta"
    assert chunks[0].line_start > 0
    assert chunks[1].line_start > chunks[0].line_start


def test_chunking_sliding_window_long_section():
    long_body = " ".join([f"sentence_{i}" for i in range(200)])
    raw = f"""# Long Section\n{long_body}"""
    parsed = parse_note(raw, stem="long_note")

    chunks = chunk_note(
        note_id="long_123",
        note=parsed,
        chunk_size=150,
        chunk_overlap=30,
    )
    assert len(chunks) > 1
    # Check that each chunk advances line indices or indices increment
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.chunk_id == f"long_123:{i}"

