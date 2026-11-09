---
title: Heading-Aware Markdown Chunking
tags: [preprocessing, chunking, markdown]
aliases: [Markdown Chunking]
---

# Heading-Aware Markdown Chunking

Chunking structured Markdown requires preserving contextual hierarchy rather than splitting blindly on character or token counts.

## Context Breadcrumbs

Each chunk created in our pipeline prepends a document breadcrumb path:
`Note Title > Heading 1 > Heading 2`

This contextual header ensures that retrieved snippets retain their semantic parentage even when severed from the main body.

## Code Fences & False Tags

Code blocks often contain comment symbols or hashtag characters that must not be parsed as Obsidian metadata:

```python
# This is a python comment, not an obsidian tag!
#notatag = 42
def example_chunker():
    return [[01-System-Architecture]]
```

Our parser masks code fences before extracting `#tags` and `[[wikilinks]]`.

