"""Parse Obsidian-flavoured Markdown into structured notes.

Extracts YAML frontmatter, tags (frontmatter + inline ``#tag``), aliases,
wikilinks/embeds, and heading-delimited sections with original line numbers.
Code fences and inline code are masked so ``#hashtags`` or ``[[links]]`` that
appear inside code are never treated as metadata.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import yaml

__all__ = ["ParsedNote", "Section", "WikiLink", "normalize_tag", "parse_note"]

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_WIKILINK_RE = re.compile(r"(!?)\[\[([^\[\]\n]+?)\]\]")
_TAG_RE = re.compile(r"(?<![\w/&#])#([A-Za-z_][\w\-/]*)")


@dataclass(frozen=True)
class WikiLink:
    """An Obsidian ``[[wikilink]]`` or ``![[embed]]``."""

    target: str
    heading: str | None = None
    alias: str | None = None
    is_embed: bool = False


@dataclass(frozen=True)
class Section:
    """Body text under one heading path, with 1-based source line numbers."""

    heading_path: tuple[str, ...]
    lines: tuple[tuple[int, str], ...]

    @property
    def text(self) -> str:
        """Section body joined back into a single string."""
        return "\n".join(line for _, line in self.lines).strip()


@dataclass
class ParsedNote:
    """Structured representation of a single note."""

    title: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    links: list[WikiLink] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_tag(raw_tag: str) -> str:
    """Normalize a tag to Obsidian's case-insensitive form without the ``#``."""
    return raw_tag.strip().lstrip("#").strip().lower()


def _as_string_list(value: Any) -> list[str]:
    """Coerce a frontmatter value (list, comma/space string, scalar) to strings."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part for part in re.split(r"[,\s]+", str(value)) if part]


def _split_frontmatter(text: str) -> tuple[dict[str, Any], int, list[str]]:
    """Return ``(frontmatter, body_start_line_index, warnings)``."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, 0, []
    body_start = text[: match.end()].count("\n")
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, body_start, ["Frontmatter is not valid YAML and was ignored."]
    if loaded is None:
        return {}, body_start, []
    if not isinstance(loaded, dict):
        return {}, body_start, ["Frontmatter is not a key/value mapping and was ignored."]
    return loaded, body_start, []


def _mask_code(lines: list[str]) -> list[str]:
    """Blank out fenced code blocks and inline code spans, preserving line count."""
    masked: list[str] = []
    in_fence = False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            masked.append("")
            continue
        masked.append("" if in_fence else _INLINE_CODE_RE.sub("", line))
    return masked


def _parse_wikilink(is_embed: str, inner: str) -> WikiLink | None:
    """Parse the inside of ``[[...]]`` into a :class:`WikiLink`."""
    target_part, _, alias = inner.partition("|")
    target, _, heading = target_part.partition("#")
    target = target.strip()
    if not target:
        return None
    return WikiLink(
        target=target,
        heading=heading.strip() or None,
        alias=alias.strip() or None,
        is_embed=bool(is_embed),
    )


def _extract_links(masked_lines: list[str]) -> list[WikiLink]:
    """Collect unique wikilinks from code-masked lines in document order."""
    links: list[WikiLink] = []
    for line in masked_lines:
        for match in _WIKILINK_RE.finditer(line):
            link = _parse_wikilink(match.group(1), match.group(2))
            if link and link not in links:
                links.append(link)
    return links


def _extract_inline_tags(masked_lines: list[str]) -> list[str]:
    """Collect inline ``#tags`` from code-masked lines, ignoring heading markers."""
    tags: list[str] = []
    for line in masked_lines:
        searchable = _HEADING_RE.sub(r"\2", line)
        tags.extend(normalize_tag(tag) for tag in _TAG_RE.findall(searchable))
    return tags


def _build_sections(lines: list[str], masked: list[str], offset: int) -> list[Section]:
    """Group body lines into sections keyed by their heading path."""
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    current: list[tuple[int, str]] = []

    def flush() -> None:
        if any(text.strip() for _, text in current):
            sections.append(Section(tuple(title for _, title in stack), tuple(current)))

    for index, (line, masked_line) in enumerate(zip(lines, masked)):
        is_heading = bool(masked_line) and _HEADING_RE.match(masked_line) is not None
        heading = _HEADING_RE.match(line) if is_heading else None
        if heading:
            flush()
            current = []
            level = len(heading.group(1))
            stack = [entry for entry in stack if entry[0] < level]
            stack.append((level, heading.group(2).strip()))
            continue
        current.append((offset + index + 1, line))
    flush()
    return sections


def _unique(values: list[str]) -> list[str]:
    """De-duplicate while preserving first-seen order and dropping empties."""
    return list(dict.fromkeys(value for value in values if value))


def parse_note(text: str, stem: str) -> ParsedNote:
    """Parse raw note text. ``stem`` is the filename without ``.md``."""
    frontmatter, body_start, warnings = _split_frontmatter(text)
    lines = text.splitlines()[body_start:]
    masked = _mask_code(lines)

    tags = [normalize_tag(tag) for tag in _as_string_list(frontmatter.get("tags", frontmatter.get("tag")))]
    tags.extend(_extract_inline_tags(masked))
    aliases = _as_string_list(frontmatter.get("aliases", frontmatter.get("alias")))
    title = str(frontmatter.get("title") or stem).strip() or stem

    for warning in warnings:
        logger.warning("Note '%s': %s", stem, warning)

    return ParsedNote(
        title=title,
        frontmatter=frontmatter,
        tags=_unique(tags),
        aliases=_unique([alias.strip() for alias in aliases]),
        links=_extract_links(masked),
        sections=_build_sections(lines, masked, body_start),
        warnings=warnings,
    )
