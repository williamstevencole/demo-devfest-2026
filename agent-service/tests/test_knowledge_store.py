from app.ingestion.store import _is_navigation_chunk


def test_un_encabezado_con_version_es_navegacion() -> None:
    assert _is_navigation_chunk("Comisiones y tarifas\nVersión: 2026-11-17")


def test_un_encabezado_solo_es_navegacion() -> None:
    assert _is_navigation_chunk("Glosario de mercado")


def test_un_chunk_con_contenido_no_es_navegacion() -> None:
    text = "Spread cambiario\nSe aplica un spread de 0.75% sobre el monto."
    assert _is_navigation_chunk(text) is False
