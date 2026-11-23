from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.errors import IngestError
from app.ingestion.chunking import DocumentChunk
from app.ingestion.ingest import ingest_knowledge
from app.ingestion.store import KnowledgeStore


class FakeEmbedding:
    def __call__(self, input: list[str]) -> list[list[float]]:
        vectors = []
        for text in input:
            lower = text.lower()
            vectors.append(
                [
                    1.0 if "regla" in lower else 0.0,
                    1.0 if "otro" in lower else 0.0,
                    0.1,
                ]
            )
        return vectors

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self(input)

    @staticmethod
    def name() -> str:
        return "fake"

    def get_config(self) -> dict:
        return {}

    def is_legacy(self) -> bool:
        return False

    @staticmethod
    def build_from_config(config: dict) -> FakeEmbedding:
        return FakeEmbedding()

    @staticmethod
    def supported_spaces() -> list[str]:
        return ["cosine", "l2", "ip"]


def test_reindexar_dos_veces_no_duplica(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "chroma", FakeEmbedding())
    chunks = [DocumentChunk("texto", "doc.md", "Regla A")]

    assert store.reindex(chunks) == 1
    assert store.reindex(chunks) == 1
    assert store.count() == 1


def test_search_devuelve_fuente_seccion_y_score(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "chroma", FakeEmbedding())
    store.reindex(
        [
            DocumentChunk("regla de concentración", "politicas.md", "Regla"),
            DocumentChunk("otro contenido", "otro.md", "Otro"),
        ]
    )

    results = store.search("regla", top_k=1)

    assert results[0].source == "politicas.md"
    assert results[0].section == "Regla"
    assert results[0].score > 0.9


def test_construir_store_no_borra_el_indice(tmp_path: Path) -> None:
    first = KnowledgeStore(tmp_path / "chroma", FakeEmbedding())
    first.reindex([DocumentChunk("regla", "doc.md", "Regla")])

    second = KnowledgeStore(tmp_path / "chroma", FakeEmbedding())

    assert second.count() == 1
    assert second.search("regla", top_k=1)[0].source == "doc.md"


def test_search_sobrevive_a_reindex_de_otro_store(tmp_path: Path) -> None:
    first = KnowledgeStore(tmp_path / "chroma", FakeEmbedding())
    first.reindex([DocumentChunk("regla", "doc.md", "Regla")])

    second = KnowledgeStore(tmp_path / "chroma", FakeEmbedding())
    second.reindex([DocumentChunk("regla nueva", "nuevo.md", "Regla nueva")])

    results = first.search("regla", top_k=1)

    assert results[0].source == "nuevo.md"


def test_ingesta_falla_si_no_hay_documentos(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "chroma", FakeEmbedding())
    store.reindex([DocumentChunk("regla", "doc.md", "Regla")])
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(IngestError):
        ingest_knowledge(empty_dir, store)
    with pytest.raises(IngestError):
        ingest_knowledge(tmp_path / "missing", store)
    assert store.count() == 1


def test_ingest_orquesta_ingestor_y_store(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "doc.md").write_text(
        "# Título\nintro\n\n## Regla A\ntexto A\n", encoding="utf-8"
    )
    store = KnowledgeStore(tmp_path / "chroma", FakeEmbedding())

    assert ingest_knowledge(knowledge_dir, store) == 1
    assert store.count() == 1


def test_ingest_route_devuelve_chunks_indexados(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.api.ingest_route.ingest_settings", lambda settings: 42)

    response = client.post("/api/ingest")

    assert response.status_code == 200
    assert response.json() == {"indexed_chunks": 42}


def test_ingest_route_mapea_error_de_ingesta(client: TestClient, monkeypatch) -> None:
    def failing_ingest(settings) -> int:
        raise IngestError("sin corpus")

    monkeypatch.setattr("app.api.ingest_route.ingest_settings", failing_ingest)

    response = client.post("/api/ingest")

    assert response.status_code == 400
    assert "sin corpus" in response.json()["detail"]
