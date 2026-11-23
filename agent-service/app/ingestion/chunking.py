"""Markdown chunking by main section."""

import re
from dataclasses import dataclass
from pathlib import Path

HEADING_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
TITLE_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class DocumentChunk:
    """One self-contained Markdown section."""

    text: str
    source: str
    section: str


def split_markdown(text: str, source: str) -> list[DocumentChunk]:
    """Split Markdown into one chunk per level-2 heading.

    Level-3 headings stay inside their parent chunk so related details are
    retrieved together. The level-1 title and version preamble are metadata,
    not a chunk.
    """

    headings = list(HEADING_PATTERN.finditer(text))
    if not headings:
        title = TITLE_PATTERN.search(text)
        section = title.group(1).strip() if title else "Documento"
        return [DocumentChunk(text=text.strip(), source=source, section=section)]

    chunks: list[DocumentChunk] = []
    for index, heading in enumerate(headings):
        next_start = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section = heading.group(1).strip()
        body = text[heading.end() : next_start].strip()
        chunk_text = f"{section}\n{body}".strip() if body else section
        chunks.append(DocumentChunk(text=chunk_text, source=source, section=section))
    return chunks


class MarkdownIngestor:
    """Load every Markdown document in a knowledge directory."""

    def __init__(self, knowledge_dir: Path) -> None:
        self._knowledge_dir = knowledge_dir

    def load_chunks(self) -> list[DocumentChunk]:
        """Return chunks from all Markdown files, ordered by filename."""

        chunks: list[DocumentChunk] = []
        for path in sorted(self._knowledge_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            chunks.extend(split_markdown(text, path.name))
        return chunks
