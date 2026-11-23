from pathlib import Path

from app.ingestion.chunking import DocumentChunk, MarkdownIngestor


def test_chunking_por_seccion_principal(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text(
        "# Título\nintro\n\n## Regla A\ntexto A\n\n### Detalle\ntexto B\n\n## Regla C\ntexto C\n",
        encoding="utf-8",
    )

    chunks = MarkdownIngestor(tmp_path).load_chunks()

    assert [chunk.section for chunk in chunks] == ["Regla A", "Regla C"]
    assert "texto A" in chunks[0].text
    assert "### Detalle" in chunks[0].text
    assert "texto B" in chunks[0].text
    assert "texto C" in chunks[1].text


def test_chunk_conserva_texto_y_fuente(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("# Título\nintro\n\n## Regla A\ntexto A\n", encoding="utf-8")

    chunks = MarkdownIngestor(tmp_path).load_chunks()

    assert chunks[0] == DocumentChunk(text="Regla A\ntexto A", source="doc.md", section="Regla A")


def test_el_titulo_y_la_version_no_son_un_chunk(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text(
        "# Título\n\nVersión: 2026-11-17\n\n## Sección real\ntexto\n",
        encoding="utf-8",
    )

    chunks = MarkdownIngestor(tmp_path).load_chunks()

    assert [chunk.section for chunk in chunks] == ["Sección real"]
    assert "Versión:" not in chunks[0].text
