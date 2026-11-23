"""Tests for the deterministic data functions behind the agent tools."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.agent.tools import payloads as agent_tools
from app.agent.tools.definitions import build_tools
from app.domain.models import Portfolio


class StubNest:
    def __init__(self, portfolio: Portfolio | None) -> None:
        self._portfolio = portfolio
        self.calls: list[str] = []

    async def get_portfolio(self, user_id: str) -> Portfolio | None:
        self.calls.append(user_id)
        if self._portfolio is None or self._portfolio.user.id != user_id:
            return None
        return self._portfolio


class StubKnowledge:
    def __init__(self, hits: list) -> None:
        self._hits = hits
        self.queries: list[tuple[str, int]] = []

    def search(self, query: str, top_k: int):
        self.queries.append((query, top_k))
        return self._hits


class StubWeb:
    def __init__(self, results: list) -> None:
        self._results = results
        self.queries: list[str] = []

    async def search(self, query: str):
        self.queries.append(query)
        return self._results


def run(coro):
    return asyncio.run(coro)


def test_analyze_portfolio_data_devuelve_cifras_del_usuario(maria: Portfolio) -> None:
    payload = run(agent_tools.analyze_portfolio_data(StubNest(maria), "maria-lopez"))

    assert payload["kind"] == "analysis"
    assert payload["user"] == "María López"
    assert payload["data"]["total_value_usd"] == 20700
    assert payload["data"]["invested_usd"] == 18200


def test_analyze_portfolio_sin_usuario_es_error(maria: Portfolio) -> None:
    payload = run(agent_tools.analyze_portfolio_data(StubNest(maria), ""))

    assert "usuario" in payload["error"]


def test_retiro_en_dolares_no_cobra_spread(maria: Portfolio) -> None:
    payload = run(
        agent_tools.withdrawal_data(StubNest(maria), "maria-lopez", 2500, convert_to_local=False)
    )

    assert payload["kind"] == "withdrawal"
    assert payload["data"]["fx_spread_usd"] == 0
    assert payload["data"]["net_amount_usd"] == 2500
    assert payload["conversion_spread_usd"] == 18.75
    assert payload["net_if_converted_usd"] == 2481.25


def test_retiro_convertido_cobra_spread(maria: Portfolio) -> None:
    payload = run(
        agent_tools.withdrawal_data(StubNest(maria), "maria-lopez", 2500, convert_to_local=True)
    )

    assert payload["data"]["fx_spread_usd"] == 18.75
    assert payload["data"]["net_amount_usd"] == 2481.25
    assert payload["net_if_converted_usd"] == 2481.25


def test_scenario_impact_calcula_exposicion_directa_e_indirecta(maria: Portfolio) -> None:
    payload = run(agent_tools.scenario_data(StubNest(maria), "maria-lopez", "NVDA", [-10, -20]))

    assert payload["kind"] == "scenario"
    exposure = payload["exposure"]
    assert exposure["direct_usd"] == 3600
    assert exposure["indirect_usd"] == 1045.5
    assert exposure["total_usd"] == 4645.5
    assert exposure["weight_invested_pct"] == 25.5
    assert payload["scenarios"][0]["move_pct"] == -10
    assert payload["scenarios"][0]["impact_usd"] == -464.55
    assert payload["scenarios"][1]["impact_usd"] == -929.1


def test_scenario_impact_resuelve_nombre_de_empresa(maria: Portfolio) -> None:
    payload = run(agent_tools.scenario_data(StubNest(maria), "maria-lopez", "NVIDIA", [-10]))

    assert payload["target"] == "NVDA"
    assert payload["exposure"]["total_usd"] == 4645.5


def test_scenario_impact_acepta_sector_en_espanol(maria: Portfolio) -> None:
    payload = run(agent_tools.scenario_data(StubNest(maria), "maria-lopez", "tecnología", [-20]))

    assert payload["target"] == "Technology"
    assert payload["exposure"]["total_usd"] == 10415


def test_scenario_impact_desconocido_lista_alternativas(maria: Portfolio) -> None:
    payload = run(agent_tools.scenario_data(StubNest(maria), "maria-lopez", "Rusia", [-10]))

    assert "error" in payload
    assert "NVDA" in payload["available_tickers"]


def test_sale_data_muestra_cambio_de_exposicion(maria: Portfolio) -> None:
    payload = run(agent_tools.sale_data(StubNest(maria), "maria-lopez", "QQQ", None))

    assert payload["kind"] == "sale"
    assert payload["data"]["cash_usd"] == 7700
    assert payload["data"]["invested_usd"] == 13000
    changes = {item["ticker"]: item for item in payload["impact"]["exposure_changes"]}
    assert changes["NVDA"]["total_change_usd"] == -468
    assert changes["NVDA"]["after_weight_pct"] == 32.1


def test_knowledge_data_devuelve_fuentes() -> None:
    hit = type(
        "Hit",
        (),
        {
            "text": "El spread es 0.75%.",
            "source": "comisiones_y_tarifas.md",
            "section": "Spread cambiario",
            "score": 0.9,
        },
    )()
    payload = agent_tools.knowledge_data(StubKnowledge([hit]), "retiro", 4)

    assert payload["kind"] == "documents"
    assert payload["documents"][0]["source"] == "comisiones_y_tarifas.md"
    assert payload["documents"][0]["section"] == "Spread cambiario"


def test_news_data_usa_la_consulta_del_agente() -> None:
    result = type(
        "Result",
        (),
        {
            "title": "Jensen Huang Resigns as Nvidia CEO",
            "url": "https://www.wired.com/story/x",
            "snippet": "Nvidia announced a transition.",
            "published_at": "2026-11-12",
            "source": "www.wired.com",
        },
    )()
    web = StubWeb([result])
    payload = run(agent_tools.news_data(web, "Jensen Huang NVIDIA renuncia"))

    assert web.queries == ["Jensen Huang NVIDIA renuncia"]
    assert payload["kind"] == "news"
    assert payload["results"][0]["url"] == "https://www.wired.com/story/x"
    assert payload["results"][0]["published_at"] == "2026-11-12"


def test_news_data_descarta_redes_si_hay_prensa() -> None:
    def result(title: str, source: str):
        return type(
            "Result",
            (),
            {
                "title": title,
                "url": f"https://{source}/story",
                "snippet": "texto",
                "published_at": "2026-11-12",
                "source": source,
            },
        )()

    web = StubWeb(
        [
            result("Post", "www.instagram.com"),
            result("Nota", "www.cnbc.com"),
        ]
    )
    payload = run(agent_tools.news_data(web, "NVIDIA"))

    assert [item["source"] for item in payload["results"]] == ["www.cnbc.com"]


def _news(title: str, published_at: str | None, source: str = "www.wired.com"):
    return type(
        "Result",
        (),
        {
            "title": title,
            "url": f"https://{source}/{title.replace(' ', '-')}",
            "snippet": title,
            "published_at": published_at,
            "source": source,
        },
    )()


def test_sources_de_noticias_incluyen_resumen_y_fecha() -> None:
    payload = {
        "kind": "news",
        "results": [
            {
                "title": "Jensen Huang Resigns as Nvidia CEO",
                "url": "https://www.wired.com/story/x",
                "source": "www.wired.com",
                "published_at": "2026-11-12",
                "snippet": "Nvidia announced a leadership transition.",
            }
        ],
    }

    sources = agent_tools.sources_from_payload(payload)

    assert sources[0]["label"] == "Jensen Huang Resigns as Nvidia CEO"
    assert "www.wired.com" in sources[0]["detail"]
    assert "2026-11-12" in sources[0]["detail"]
    assert "Nvidia announced a leadership transition." in sources[0]["detail"]


def test_news_data_ordena_y_expone_la_mas_reciente() -> None:
    web = StubWeb(
        [
            _news("Huang renuncia", "2026-11-12"),
            _news("Huang vuelve", "2026-11-17"),
        ]
    )

    payload = run(agent_tools.news_data(web, "Jensen Huang"))

    assert payload["latest"]["title"] == "Huang vuelve"
    assert [item["published_at"] for item in payload["timeline"]] == [
        "2026-11-17",
        "2026-11-12",
    ]
    assert "más reciente" in payload["note"]


def test_news_data_sin_fechas_no_rompe_el_orden() -> None:
    web = StubWeb([_news("Sin fecha", None), _news("Con fecha", "2026-11-17")])

    payload = run(agent_tools.news_data(web, "NVIDIA"))

    assert payload["timeline"][0]["published_at"] == "2026-11-17"
    assert payload["latest"]["title"] == "Con fecha"


def test_scenario_default_incluye_subida_y_bajada(maria: Portfolio) -> None:
    payload = run(agent_tools.scenario_data(StubNest(maria), "maria-lopez", "NVDA"))

    assert [item["move_pct"] for item in payload["scenarios"]] == [-20.0, -10.0, 10.0, 20.0]
    assert payload["scenarios"][2]["impact_usd"] == 464.55
    assert payload["scenarios"][3]["impact_usd"] == 929.1


@pytest.mark.parametrize("target", ["NVDA", "Technology"])
def test_scenario_target_es_case_insensitive(maria: Portfolio, target: str) -> None:
    payload = run(agent_tools.scenario_data(StubNest(maria), "maria-lopez", target.lower(), [-10]))

    assert "error" not in payload


def test_retiro_incluye_la_cita_de_tarifas(maria: Portfolio) -> None:
    payload = run(
        agent_tools.withdrawal_data(StubNest(maria), "maria-lopez", 2500, convert_to_local=True)
    )

    assert payload["citation"]["source"] == "comisiones_y_tarifas.md"
    assert payload["citation"]["section"] == "Retiro y plazos"


class FailingWeb:
    async def search(self, query: str):
        raise RuntimeError("Tavily caído")


def test_una_tool_que_falla_devuelve_error_estructurado() -> None:
    container = SimpleNamespace(
        web=FailingWeb(),
        knowledge=None,
        nest=None,
        settings=SimpleNamespace(retrieval_top_k=4),
    )
    tool = next(item for item in build_tools(container) if item.name == "search_news")

    raw = run(tool.ainvoke({"query": "NVIDIA"}))

    payload = json.loads(raw)
    assert payload["error"] == "La herramienta search_news falló. Intenta de nuevo."
    assert payload["tool"] == "search_news"


def test_search_news_permite_verificar_el_estado_actual() -> None:
    container = SimpleNamespace(
        web=StubWeb([]),
        knowledge=None,
        nest=None,
        settings=SimpleNamespace(retrieval_top_k=4),
    )
    tool = next(item for item in build_tools(container) if item.name == "search_news")

    assert "una sola búsqueda" not in tool.description
    assert "estado actual" in tool.description
    assert "3 veces" in tool.description


def test_simulate_sale_no_se_ofrece_para_recomendaciones_generales() -> None:
    container = SimpleNamespace(
        web=StubWeb([]),
        knowledge=None,
        nest=None,
        settings=SimpleNamespace(retrieval_top_k=4),
    )
    tools = {item.name: item for item in build_tools(container)}

    simulate = " ".join(tools["simulate_sale"].description.split())
    withdrawal = " ".join(tools["estimate_withdrawal"].description.split())
    portfolio = " ".join(tools["analyze_portfolio"].description.split())
    assert "No la uses para recomendaciones generales" in simulate
    assert "no la uses para recomendaciones generales de inversión" in withdrawal
    assert "recomendaciones generales de inversión" in portfolio
