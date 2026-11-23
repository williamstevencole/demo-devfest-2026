"""Thin adapter over the Chroma knowledge store."""

from app.ingestion.store import KnowledgeStore, RetrievedDoc


class KnowledgeTool:
    """Search the local corpus through the persistent store."""

    def __init__(self, store: KnowledgeStore) -> None:
        self._store = store

    def search(self, query: str, top_k: int) -> list[RetrievedDoc]:
        """Return the closest chunks for a query."""

        return self._store.search(query, top_k)
