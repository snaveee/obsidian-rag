"""Heading-aware sliding-window chunking for parsed notes.

Each section is split into windows of roughly ``chunk_size`` characters with
``chunk_overlap`` characters carried over. Windows never cross heading
boundaries, every chunk records its source line range, and the embedded text
is prefixed with a ``Title > Heading > Subheading`` breadcrumb so both BM25
and the dense retriever see where the passage lives.
"""

from dataclasses import dataclass

from infra.markdown_parser import ParsedNote, Section

__all__ = ["Chunk", "chunk_note"]

_Unit = tuple[int, str]


@dataclass(frozen=True)
class Chunk:
    """A retrievable passage of a note."""

    chunk_id: str
    note_id: str
    chunk_index: int
    text: str
    heading_path: str
    line_start: int
    line_end: int


def _split_long_line(line_no: int, line: str, chunk_size: int) -> list[_Unit]:
    """Split a line longer than ``chunk_size`` into word-bounded pieces."""
    pieces: list[_Unit] = []
    current = ""
    for word in line.split():
        while len(word) > chunk_size:
            if current:
                pieces.append((line_no, current))
                current = ""
            pieces.append((line_no, word[:chunk_size]))
            word = word[chunk_size:]
        candidate = f"{current} {word}".strip()
        if len(candidate) > chunk_size and current:
            pieces.append((line_no, current))
            candidate = word
        current = candidate
    if current:
        pieces.append((line_no, current))
    return pieces


def _to_units(section: Section, chunk_size: int) -> list[_Unit]:
    """Flatten a section into line units no longer than ``chunk_size``."""
    units: list[_Unit] = []
    for line_no, line in section.lines:
        if len(line) > chunk_size:
            units.extend(_split_long_line(line_no, line, chunk_size))
        else:
            units.append((line_no, line))
    return units


def _windows(units: list[_Unit], chunk_size: int, chunk_overlap: int) -> list[list[_Unit]]:
    """Group units into overlapping windows; always makes forward progress."""
    windows: list[list[_Unit]] = []
    start = 0
    while start < len(units):
        end, total = start, 0
        while end < len(units) and (end == start or total + len(units[end][1]) <= chunk_size):
            total += len(units[end][1]) + 1
            end += 1
        windows.append(units[start:end])
        if end >= len(units):
            break
        back, carried = end, 0
        while back > start + 1 and carried < chunk_overlap:
            back -= 1
            carried += len(units[back][1]) + 1
        start = back
    return windows


def chunk_note(note_id: str, note: ParsedNote, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """Split a parsed note into heading-aware, line-addressed chunks."""
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and smaller than a positive chunk_size.")

    chunks: list[Chunk] = []
    for section in note.sections:
        heading_path = " > ".join(section.heading_path)
        breadcrumb = " > ".join((note.title, *section.heading_path))
        for window in _windows(_to_units(section, chunk_size), chunk_size, chunk_overlap):
            body = "\n".join(text for _, text in window).strip()
            if not body:
                continue
            index = len(chunks)
            chunks.append(
                Chunk(
                    chunk_id=f"{note_id}:{index}",
                    note_id=note_id,
                    chunk_index=index,
                    text=f"{breadcrumb}\n\n{body}",
                    heading_path=heading_path,
                    line_start=window[0][0],
                    line_end=window[-1][0],
                )
            )
    return chunks
