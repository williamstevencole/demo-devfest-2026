from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"


def test_corpus_tiene_seis_documentos_y_no_filtra_datos() -> None:
    docs = list(KNOWLEDGE_DIR.glob("*.md"))

    assert len(docs) == 6
    combined = "\n".join(path.read_text(encoding="utf-8") for path in docs)
    for forbidden in ("maria-lopez", "NVDA 20", "$180.00", "Reuters"):
        assert forbidden not in combined
    assert "10-K" not in combined
    for path in docs:
        assert "2026-11-17" in path.read_text(encoding="utf-8")


def test_secciones_que_usa_el_guion_de_chips() -> None:
    politicas = (KNOWLEDGE_DIR / "politicas_de_inversion_y_riesgo.md").read_text(encoding="utf-8")
    productos = (KNOWLEDGE_DIR / "productos_disponibles.md").read_text(encoding="utf-8")
    comisiones = (KNOWLEDGE_DIR / "comisiones_y_tarifas.md").read_text(encoding="utf-8")

    assert "## Diversificación" in politicas
    assert "25%" not in politicas
    assert "## Composición tecnológica de VOO" in productos
    assert "### Qué replica VOO" in productos
    assert "QQQ" not in productos
    comisiones_flat = " ".join(comisiones.split())
    assert "## Comisiones y retiro" in comisiones
    assert "### Spread cambiario" in comisiones
    assert "### Ejemplo de costo de retiro" in comisiones
    assert "$18.75" in comisiones
    assert "tipo de cambio" in comisiones_flat
    assert "\n## Comisión de acciones y ETFs" not in comisiones
