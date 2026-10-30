"""Sentence-level chunking with exact offsets into the original document."""

import re
from dataclasses import dataclass

# Sentence ends: . ! ? Arabic question mark, or newline. A dot between two digits (6.5) is not a boundary.
_BOUNDARY = re.compile(r"(?<!\d)\.|\.(?!\d)|[!?؟]|\n+")


@dataclass(frozen=True)
class Chunk:
    ord: int
    start: int
    end: int
    text: str


def chunk(text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    start = 0
    for m in _BOUNDARY.finditer(text):
        end = m.end()
        _add(chunks, text, start, end)
        start = end
    _add(chunks, text, start, len(text))
    return chunks


def _add(chunks: list[Chunk], text: str, start: int, end: int) -> None:
    seg = text[start:end]
    lead = len(seg) - len(seg.lstrip())
    trail = len(seg) - len(seg.rstrip())
    s, e = start + lead, end - trail
    if e > s:
        chunks.append(Chunk(len(chunks), s, e, text[s:e]))
