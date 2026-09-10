"""Frontmatter parsing + markdown chunking. Pure functions, no I/O (see `rag`/`ingestion` skills)."""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*\n?", re.DOTALL)

# Word-count approximation of the `rag` skill's 400-800 token / 10-15% overlap
# chunking rule. No tiktoken dependency needed: the embedding model is local.
TARGET_CHUNK_WORDS = 600
OVERLAP_WORDS = 80


@dataclass
class DocumentMeta:
    title: str
    department: str | None
    version: int
    supersedes: str | None
    references: list[str]


@dataclass
class Chunk:
    chunk_index: int
    section: str | None
    content: str


def parse_document(raw_text: str) -> tuple[DocumentMeta, str]:
    """Split a corpus markdown file into its frontmatter metadata and body."""
    match = _FRONTMATTER_RE.match(raw_text)
    if not match:
        raise ValueError("document is missing a YAML frontmatter block")

    front = yaml.safe_load(match.group(1)) or {}
    if "title" not in front:
        raise ValueError("frontmatter is missing required field 'title'")

    meta = DocumentMeta(
        title=front["title"],
        department=front.get("department"),
        version=int(front.get("version", 1)),
        supersedes=front.get("supersedes"),
        references=front.get("references") or [],
    )
    return meta, raw_text[match.end():]


def chunk_markdown(body: str) -> list[Chunk]:
    """Chunk by `##` heading first, then by word count within an oversized section."""
    chunks: list[Chunk] = []
    for section_title, section_text in _split_by_heading(body):
        for piece in _split_by_words(section_text):
            chunks.append(Chunk(chunk_index=len(chunks), section=section_title, content=piece))
    return chunks


def _split_by_heading(body: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in body.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, current_lines))

    return [
        (title, text)
        for title, lines in sections
        if (text := "\n".join(lines).strip())
    ]


def _split_by_words(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= TARGET_CHUNK_WORDS:
        return [text]

    pieces: list[str] = []
    step = TARGET_CHUNK_WORDS - OVERLAP_WORDS
    start = 0
    while start < len(words):
        pieces.append(" ".join(words[start : start + TARGET_CHUNK_WORDS]))
        if start + TARGET_CHUNK_WORDS >= len(words):
            break
        start += step
    return pieces
