"""Persistent ChromaDB knowledge store."""

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path

import chromadb
from chromadb.api.types import EmbeddingFunction

from app.ingestion.chunking import DocumentChunk

COLLECTION_NAME = "broker_knowledge"
COSINE_SPACE = "cosine"
NAVIGATION_FETCH_EXTRA = 4


def _is_navigation_chunk(text: str) -> bool:
    """Return True for a heading-only chunk with no real content."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return True
    if any(line.lower().startswith("versión:") for line in lines):
        return True
    if len(lines) == 1:
        words = lines[0].split()
        return len(words) <= 6 and not lines[0].endswith((".", "?", "!"))
    return False


@dataclass(frozen=True)
class RetrievedDoc:
    """A knowledge chunk returned by a similarity search."""

    text: str
    source: str
    section: str
    score: float


class KnowledgeStore:
    """Idempotent Chroma collection over the Markdown corpus."""

    def __init__(self, persist_dir: Path, embedding_function: EmbeddingFunction) -> None:
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._embedding_function = embedding_function
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": COSINE_SPACE},
        )

    def _recreate_collection(self):
        existing = {collection.name for collection in self._client.list_collections()}
        if COLLECTION_NAME in existing:
            self._client.delete_collection(COLLECTION_NAME)
        return self._client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": COSINE_SPACE},
        )

    def _refresh_collection(self):
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": COSINE_SPACE},
        )

    def reindex(self, chunks: list[DocumentChunk]) -> int:
        """Replace the collection contents and return the indexed count."""

        self._collection = self._recreate_collection()
        unique = {
            sha1(f"{chunk.source}:{chunk.section}".encode()).hexdigest(): chunk for chunk in chunks
        }
        if unique:
            self._collection.add(
                ids=list(unique),
                documents=[chunk.text for chunk in unique.values()],
                metadatas=[
                    {"source": chunk.source, "section": chunk.section} for chunk in unique.values()
                ],
            )
        return len(unique)

    def _search(self, query: str, top_k: int) -> list[RetrievedDoc]:
        if self._collection.count() == 0:
            return []
        result = self._collection.query(
            query_texts=[query],
            n_results=top_k + NAVIGATION_FETCH_EXTRA,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents") or [[]]
        metadatas = result.get("metadatas") or [[]]
        distances = result.get("distances") or [[]]
        matches = [
            RetrievedDoc(
                text=text,
                source=metadata["source"],
                section=metadata["section"],
                score=max(0.0, 1.0 - distance),
            )
            for text, metadata, distance in zip(
                documents[0], metadatas[0], distances[0], strict=True
            )
        ]
        content = [match for match in matches if not _is_navigation_chunk(match.text)]
        return (content or matches)[:top_k]

    def search(self, query: str, top_k: int) -> list[RetrievedDoc]:
        """Return the closest chunks for a query.

        The collection can be replaced by a separate ingestion process while this
        store is alive. If the cached handle was invalidated, refresh it once and
        retry instead of failing the agent tool.
        """

        try:
            return self._search(query, top_k)
        except Exception:
            self._refresh_collection()
            return self._search(query, top_k)

    def count(self) -> int:
        """Return how many chunks are indexed."""

        return self._collection.count()
