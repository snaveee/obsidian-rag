"""Unit tests for Markdown parsing, frontmatter, tags, and wikilinks."""

from infra.markdown_parser import normalize_tag, parse_note


def test_normalize_tag():
    assert normalize_tag("#Architecture") == "architecture"
    assert normalize_tag("rag-system") == "rag-system"
    assert normalize_tag("#Dev/Ops") == "dev/ops"


def test_parse_frontmatter_and_inline_tags():
    raw = """---
title: Advanced Vector Systems
tags: [architecture, vector-search]
aliases: [VectorSys]
---

# Heading 1
Some body text with an inline #optimization tag.

## Heading 2
Another section with #dev/ops tag.
"""
    parsed = parse_note(raw, stem="note-stem")
    assert parsed.title == "Advanced Vector Systems"
    assert "architecture" in parsed.tags
    assert "vector-search" in parsed.tags
    assert "optimization" in parsed.tags
    assert "dev/ops" in parsed.tags
    assert "VectorSys" in parsed.aliases
    assert len(parsed.sections) >= 2


def test_code_fences_mask_comments_and_tags():
    raw = """---
title: Code Sample Note
---

# Code Section
Here is python code:

```python
# This is a comment, not a tag!
#notatag = 123
def get_link():
    return "[[FakeLinkInCode]]"
```

And real text referencing [[ActualNote]] with #real-tag.
"""
    parsed = parse_note(raw, stem="code_sample")
    assert "notatag" not in parsed.tags
    assert "real-tag" in parsed.tags

    link_targets = [link.target for link in parsed.links]
    assert "ActualNote" in link_targets
    assert "FakeLinkInCode" not in link_targets


def test_wikilink_variants():
    raw = """
Look at [[SimpleNote]], or [[AliasedNote|Custom Title]],
and [[HeadingNote#Specific Header]].
Also an embed: ![[ImageOrNote.png]].
"""
    parsed = parse_note(raw, stem="links_note")
    targets = {l.target: l for l in parsed.links}

    assert "SimpleNote" in targets
    assert targets["AliasedNote"].alias == "Custom Title"
    assert targets["HeadingNote"].heading == "Specific Header"
    assert targets["ImageOrNote.png"].is_embed is True

