"""Tests for the final-answer grounding guard."""

from langchain_core.messages import ToolMessage

from app.agent.grounding import (
    allowed_sections_from_messages,
    allowed_urls_from_messages,
    fix_malformed_percentages,
    strip_tool_citations,
    strip_unknown_sections,
    strip_unknown_urls,
)


def _news_tool_message() -> ToolMessage:
    return ToolMessage(
        content=(
            '{"kind":"news","results":[{"title":"CNBC",'
            '"url":"https://www.cnbc.com/2026/11/12/nvidia-jensen-huang-ceo-live-updates.html"}]}'
        ),
        name="search_news",
        tool_call_id="call-1",
    )


def test_elimina_url_que_no_vino_de_una_tool() -> None:
    message = _news_tool_message()
    allowed = allowed_urls_from_messages([message])
    answer = (
        "La noticia salió en CNBC, 13/11/2026, "
        "https://www.cnbc.com/2026/11/12/nvidia-ceo-jensen-huang-resigns-live-updates.html."
    )

    cleaned = strip_unknown_urls(answer, allowed)

    assert "resigns-live-updates" not in cleaned
    assert "CNBC, 13/11/2026" in cleaned


def test_conserva_url_que_vino_de_una_tool() -> None:
    message = _news_tool_message()
    allowed = allowed_urls_from_messages([message])
    url = "https://www.cnbc.com/2026/11/12/nvidia-jensen-huang-ceo-live-updates.html"
    answer = f"La noticia salió en CNBC ({url})."

    cleaned = strip_unknown_urls(answer, allowed)

    assert url in cleaned
    assert cleaned == f"La noticia salió en CNBC ({url})."


def _knowledge_tool_message() -> ToolMessage:
    return ToolMessage(
        content=(
            '{"kind":"documents","documents":[{'
            '"source":"comisiones_y_tarifas.md","section":"Retiro y plazos",'
            '"text":"El retiro tarda 2 a 3 días hábiles."}]}'
        ),
        name="search_knowledge",
        tool_call_id="call-2",
    )


def test_elimina_seccion_que_no_vino_de_una_tool() -> None:
    allowed = allowed_sections_from_messages([_knowledge_tool_message()])
    answer = "Puedes consultar comisiones_y_tarifas.md, sección Retiros y transferencias."

    cleaned = strip_unknown_sections(answer, allowed)

    assert "Retiros y transferencias" not in cleaned
    assert "comisiones_y_tarifas.md" in cleaned


def test_conserva_seccion_exacta() -> None:
    allowed = allowed_sections_from_messages([_knowledge_tool_message()])
    answer = "Puedes consultar comisiones_y_tarifas.md, sección Retiro y plazos."

    cleaned = strip_unknown_sections(answer, allowed)

    assert cleaned == answer


def test_allowed_sections_lee_la_cita_de_un_retiro() -> None:
    message = ToolMessage(
        content=(
            '{"kind":"withdrawal","citation":{'
            '"source":"comisiones_y_tarifas.md","section":"Retiro y plazos"}}'
        ),
        name="estimate_withdrawal",
        tool_call_id="call-3",
    )

    allowed = allowed_sections_from_messages([message])

    assert allowed == {"comisiones_y_tarifas.md": {"Retiro y plazos"}}


def test_limpia_enfasis_markdown_alrededor_del_archivo() -> None:
    allowed = allowed_sections_from_messages([_knowledge_tool_message()])
    answer = "Según *comisiones_y_tarifas.md, sección Retiro y plazos."

    cleaned = strip_unknown_sections(answer, allowed)

    assert "*comisiones" not in cleaned
    assert cleaned.startswith("Según comisiones_y_tarifas.md")


def test_corrige_porcentaje_con_punto_extra() -> None:
    answer = "un 26.9.5% del total con efectivo"

    assert fix_malformed_percentages(answer) == "un 26.95% del total con efectivo"


def test_no_toca_porcentajes_bien_formados() -> None:
    answer = "32.1% de lo invertido y 26.95% del total"

    assert fix_malformed_percentages(answer) == answer


def test_elimina_citas_a_herramientas() -> None:
    answer = "El impacto sería de -$417.75 (scenario_impact, 2026-11-23)."

    cleaned = strip_tool_citations(answer)

    assert cleaned == "El impacto sería de -$417.75."


def test_elimina_cita_que_mezcla_fuente_y_herramienta() -> None:
    answer = "Tienes $4,177.50 (NVIDIA Corporation, 2026-11-17, analyze_portfolio)."

    cleaned = strip_tool_citations(answer)

    assert "analyze_portfolio" not in cleaned
    assert "NVIDIA Corporation" not in cleaned
    assert cleaned == "Tienes $4,177.50."


def test_no_toca_una_cita_de_noticia() -> None:
    answer = "Lo reinstalaron (CNBC, 23/11/2026, https://www.cnbc.com/nota)."

    assert strip_tool_citations(answer) == answer


def test_url_eliminada_no_deja_coma_colgando() -> None:
    allowed = allowed_urls_from_messages([_news_tool_message()])
    answer = "Reportó resultados el 17/11/2026 (17/11/2026, https://inventado.example/nota)."

    cleaned = strip_unknown_urls(answer, allowed)

    assert "(17/11/2026)" in cleaned
    assert ",)" not in cleaned
