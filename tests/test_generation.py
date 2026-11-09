"""Unit tests for grounded generation, context block assembly, and citation parsing."""

from infra.generation import (
    NOT_FOUND_SENTINEL,
    build_context_block,
    extract_citations,
    generate_answer,
)


def test_build_context_block():
    results = [
        {"title": "Note Alpha", "heading_path": "Heading 1", "text": "Content of alpha."},
        {"title": "Note Beta", "heading_path": "", "text": "Content of beta."},
    ]
    block = build_context_block(results)
    assert "[Reference 1]" in block
    assert "Note: Note Alpha" in block
    assert "[Reference 2]" in block
    assert "Heading: Top level" in block


def test_extract_citations():
    text = "According to [1] and [Reference 2], the system design relies on [3]."
    cites = extract_citations(text, total_sources=3)
    assert cites == [1, 2, 3]

    # Ignore out-of-bound citations
    cites_oob = extract_citations("Refer to [99]", total_sources=3)
    assert cites_oob == []


def test_generate_answer_empty_results():
    ans = generate_answer("What is X?", results=[])
    assert ans.answer == NOT_FOUND_SENTINEL
    assert ans.citations == []
    assert ans.sources == []

