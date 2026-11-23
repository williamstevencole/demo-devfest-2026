"""Knowledge ingestion orchestration."""

import json
from pathlib import Path

from app.config import Settings, get_settings
from app.errors import IngestError
from app.ingestion.chunking import MarkdownIngestor
from app.ingestion.store import KnowledgeStore


def build_embedding_function(settings: Settings):
    """Build the local multilingual embedding function."""

    from chromadb.utils.embedding_functions import (
        SentenceTransformerEmbeddingFunction,
    )

    return SentenceTransformerEmbeddingFunction(model_name=settings.embedding_model)


def ingest_knowledge(knowledge_dir: Path, store: KnowledgeStore) -> int:
    """Chunk a knowledge directory and replace the store contents."""

    if not knowledge_dir.is_dir():
        raise IngestError(f"Knowledge directory not found: {knowledge_dir}")
    chunks = MarkdownIngestor(knowledge_dir).load_chunks()
    if not chunks:
        raise IngestError(f"No Markdown documents found in {knowledge_dir}")
    return store.reindex(chunks)


def ingest_settings(settings: Settings) -> int:
    """Index the corpus configured for this process."""

    store = KnowledgeStore(settings.chroma_dir, build_embedding_function(settings))
    return ingest_knowledge(settings.knowledge_dir, store)


def main() -> None:
    """Run ingestion from the command line and print the chunk count."""

    indexed = ingest_settings(get_settings())
    print(json.dumps({"indexed_chunks": indexed}))


if __name__ == "__main__":
    main()
