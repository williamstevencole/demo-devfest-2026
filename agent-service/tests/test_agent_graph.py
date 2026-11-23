"""Tests for the autonomous tool-calling agent graph."""

import asyncio
import logging
from datetime import date
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph import build_agent_graph
from app.agent.nodes import MAX_TOOL_ROUNDS, make_agent_node
from app.agent.nodes.agent import (
    _decision_detail,
    _decision_title,
    _needs_personal_data,
)


class StubNest:
    def __init__(self, portfolio) -> None:
        self._portfolio = portfolio

    async def get_portfolio(self, user_id: str):
        if self._portfolio is None or self._portfolio.user.id != user_id:
            return None
        return self._portfolio


class StubKnowledge:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str, top_k: int):
        self.queries.append(query)
        return [
            SimpleNamespace(
                text="Un ETF es un fondo que se negocia en bolsa.",
                source="glosario_de_mercado.md",
                section="ETF",
                score=0.9,
            )
        ]


class StubWeb:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str):
        self.queries.append(query)
        return [
            SimpleNamespace(
                title="Jensen Huang Resigns as Nvidia CEO",
                url="https://www.wired.com/story/nvidia-ceo-jensen-huang-steps-down",
                snippet="Nvidia announced a leadership transition.",
                published_at="2026-11-12",
                source="www.wired.com",
            )
        ]


class ScriptedLLM:
    def __init__(self, responses: list[AIMessage], final_answer: str = "Respuesta final.") -> None:
        self._responses = list(responses)
        self._final_answer = final_answer
        self.calls: list[list] = []
        self.tools = []

    def bind_tools(self, tools):
        self.tools = list(tools)
        return self

    async def ainvoke(self, messages):
        self.calls.append(list(messages))
        if self._responses:
            return self._responses.pop(0)
        return AIMessage(content=self._final_answer)


def _container(maria):
    return SimpleNamespace(
        nest=StubNest(maria),
        knowledge=StubKnowledge(),
        web=StubWeb(),
        llm=None,
        settings=SimpleNamespace(retrieval_top_k=4),
    )


def _run(graph, state):
    async def collect():
        values = None
        custom = []
        async for mode, chunk in graph.astream(state, stream_mode=["custom", "values"]):
            if mode == "custom":
                custom.append(chunk)
            elif mode == "values":
                values = chunk
        return values, custom

    return asyncio.run(collect())


def test_agente_elige_noticia_y_escenario(maria) -> None:
    llm = ScriptedLLM(
        [
            AIMessage(
                content="Voy a revisar la noticia y calcular tu exposición a NVIDIA.",
                tool_calls=[
                    {
                        "name": "search_news",
                        "args": {"query": "Jensen Huang NVIDIA renuncia"},
                        "id": "call-news",
                    },
                    {
                        "name": "scenario_impact",
                        "args": {"target": "NVDA", "moves_pct": [-10, -20]},
                        "id": "call-scenario",
                    },
                ],
            ),
        ],
        final_answer=("NVIDIA es el 25.5% de tu invertido. Una caída del 20% serían $929."),
    )
    container = _container(maria)
    container.llm = llm
    graph = build_agent_graph(container)

    final, custom = _run(
        graph,
        {
            "messages": [HumanMessage(content="¿Me afecta la salida de Jensen Huang?")],
            "user_id": "maria-lopez",
            "query": "¿Me afecta la salida de Jensen Huang?",
            "tool_rounds": 0,
        },
    )

    assert final["answer"].startswith("NVIDIA es el 25.5%")
    assert final["sources"][0]["url"].startswith("https://www.wired.com")
    assert any(step["kind"] == "decision" for step in final["trace"])
    assert any(step["kind"] == "web_search" for step in final["trace"])
    assert any(step["title"] == "Calcular el impacto" for step in final["trace"])
    assert any(step["title"] == "Redactar la respuesta" for step in final["trace"])
    assert any(event.get("kind") == "tool_call" for event in custom)


def test_agente_expone_el_retiro_determinista(maria) -> None:
    llm = ScriptedLLM(
        [
            AIMessage(
                content="Voy a calcular el retiro.",
                tool_calls=[
                    {
                        "name": "estimate_withdrawal",
                        "args": {"amount_usd": 2500, "convert_to_local": False},
                        "id": "call-withdrawal",
                    }
                ],
            ),
        ],
        final_answer="Puedes retirar $2,500 en dólares sin spread.",
    )
    container = _container(maria)
    container.llm = llm
    graph = build_agent_graph(container)

    final, _ = _run(
        graph,
        {
            "messages": [HumanMessage(content="¿Puedo retirar $2,500?")],
            "user_id": "maria-lopez",
            "query": "¿Puedo retirar $2,500?",
            "tool_rounds": 0,
        },
    )

    assert any(step["title"] == "Calcular el retiro de $2,500.00" for step in final["trace"])
    assert final["disclaimer_required"] is True


def test_agente_responde_general_sin_pedir_usuario() -> None:
    llm = ScriptedLLM(
        [
            AIMessage(
                content="Busco en el glosario.",
                tool_calls=[
                    {
                        "name": "search_knowledge",
                        "args": {"query": "qué es un ETF"},
                        "id": "call-knowledge",
                    }
                ],
            ),
        ],
        final_answer="Un ETF es un fondo que se negocia en bolsa.",
    )
    container = _container(None)
    container.llm = llm
    graph = build_agent_graph(container)

    final, _ = _run(
        graph,
        {
            "messages": [HumanMessage(content="¿Qué es un ETF?")],
            "user_id": "",
            "query": "¿Qué es un ETF?",
            "tool_rounds": 0,
        },
    )

    assert final["sources"][0]["label"] == "glosario_de_mercado.md > ETF"
    titles = [step["title"] for step in final["trace"]]
    assert "Buscar en el conocimiento del broker: «qué es un ETF»" in titles
    retrieval = next(step for step in final["trace"] if step["kind"] == "retrieval")
    assert "1 documento encontrado" in retrieval["detail"]


def test_agente_corta_el_bucle_al_llegar_al_presupuesto(maria) -> None:
    tool_call = AIMessage(
        content="Sigo buscando.",
        tool_calls=[
            {
                "name": "scenario_impact",
                "args": {"target": "NVDA"},
                "id": "call-loop",
            }
        ],
    )
    llm = ScriptedLLM(
        [tool_call for _ in range(MAX_TOOL_ROUNDS + 2)],
        final_answer="Respuesta de emergencia.",
    )
    container = _container(maria)
    container.llm = llm
    graph = build_agent_graph(container)

    final, _ = _run(
        graph,
        {
            "messages": [HumanMessage(content="¿Me afecta NVDA?")],
            "user_id": "maria-lopez",
            "query": "¿Me afecta NVDA?",
            "tool_rounds": 0,
        },
    )

    assert final["tool_rounds"] <= MAX_TOOL_ROUNDS
    assert final["answer"]
    assert len(llm.calls) <= MAX_TOOL_ROUNDS + 2


class FailingLLM:
    def __init__(self) -> None:
        self.calls = 0

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        self.calls += 1
        raise RuntimeError("429 quota exceeded")


def test_agente_responde_si_el_modelo_falla(maria) -> None:
    container = _container(maria)
    failing = FailingLLM()
    container.llm = failing
    graph = build_agent_graph(container)

    final, _ = _run(
        graph,
        {
            "messages": [HumanMessage(content="¿Cuánto tengo en efectivo?")],
            "user_id": "maria-lopez",
            "query": "¿Cuánto tengo en efectivo?",
            "tool_rounds": 0,
        },
    )

    assert "No pude consultar el modelo" in final["answer"]
    assert final["llm_error"] is True
    assert failing.calls == 1


def test_fallo_del_modelo_se_registra_en_el_log(maria, caplog) -> None:
    container = _container(maria)
    container.llm = FailingLLM()
    graph = build_agent_graph(container)

    with caplog.at_level(logging.ERROR):
        _run(
            graph,
            {
                "messages": [HumanMessage(content="¿Cuánto tengo en efectivo?")],
                "user_id": "maria-lopez",
                "query": "¿Cuánto tengo en efectivo?",
                "tool_rounds": 0,
            },
        )

    assert "modelo" in caplog.text.lower()
    assert "429 quota exceeded" in caplog.text


def test_decicion_generica_se_reemplaza_con_la_accion_real() -> None:
    response = AIMessage(
        content="Consultando las herramientas necesarias.",
        tool_calls=[
            {"name": "analyze_portfolio", "args": {}, "id": "call-analysis"},
            {"name": "scenario_impact", "args": {"target": "Technology"}, "id": "call-impact"},
        ],
    )

    assert _decision_title(response) == (
        "Revisar tu portafolio y calcular el impacto de Technology"
    )
    assert "herramienta" not in _decision_detail(response).lower()


def test_decicion_especifica_del_modelo_se_conserva() -> None:
    response = AIMessage(
        content="Voy a buscar la noticia y estimar el retiro.",
        tool_calls=[{"name": "search_news", "args": {"query": "x"}, "id": "call-news"}],
    )

    assert _decision_detail(response) == "Voy a buscar la noticia y estimar el retiro."
    assert _decision_title(response) == "Buscar noticias: «x»"


def test_traza_de_decicion_no_muestra_la_frase_generica(maria) -> None:
    llm = ScriptedLLM(
        [
            AIMessage(
                content="Consultando las herramientas necesarias.",
                tool_calls=[
                    {"name": "search_news", "args": {"query": "energía"}, "id": "call-news"}
                ],
            ),
        ],
        final_answer="Respuesta final.",
    )
    container = _container(maria)
    container.llm = llm
    graph = build_agent_graph(container)

    _, custom = _run(
        graph,
        {
            "messages": [HumanMessage(content="¿Me afecta una guerra energética?")],
            "user_id": "maria-lopez",
            "query": "¿Me afecta una guerra energética?",
            "tool_rounds": 0,
        },
    )

    decisions = [step for step in custom if step["kind"] == "decision"]
    assert decisions[0]["title"] == "Buscar noticias: «energía»"
    assert decisions[0]["detail"] == "El modelo decidió qué consultar en esta ronda."


def test_preguntas_personales_fuerzan_datos_frescos() -> None:
    assert _needs_personal_data("¿En qué sector me recomendarías comprar?")
    assert _needs_personal_data("analiza mi portafolio")
    assert _needs_personal_data("¿Puedo retirar $5,000 hoy?")
    assert _needs_personal_data("¿Y si vendo VOO?")


def test_preguntas_generales_no_fuerzan_tools() -> None:
    assert not _needs_personal_data("Hola :D")
    assert not _needs_personal_data("¿Qué es un ETF y cuánto cobran por retirar?")
    assert not _needs_personal_data("¿Qué es la diversificación?")


class _ChoiceRunner:
    def __init__(self, owner, tool_choice) -> None:
        self._owner = owner
        self._tool_choice = tool_choice

    async def ainvoke(self, messages):
        self._owner.used.append(self._tool_choice)
        return AIMessage(content="Listo.")


class ChoiceModel:
    """Records which tool_choice was active when the model was invoked."""

    def __init__(self) -> None:
        self.used: list = []

    def bind_tools(self, tools, tool_choice=None):
        return _ChoiceRunner(self, tool_choice)


def _first_choice(query: str):
    llm = ChoiceModel()
    node = make_agent_node(llm, [])
    asyncio.run(
        node(
            {
                "messages": [HumanMessage(content=query)],
                "query": query,
                "tool_rounds": 0,
            }
        )
    )
    return llm.used[0]


def test_pregunta_me_afecta_deja_que_el_llm_elija_la_tool() -> None:
    assert _first_choice("¿Me afecta la salida de Jensen Huang de NVIDIA?") == "any"


def test_pregunta_personal_sigue_forzando_alguna_tool() -> None:
    assert _first_choice("Analiza mi portafolio") == "any"


def test_pregunta_general_no_fuerza_tool_choice() -> None:
    assert _first_choice("¿Qué es un ETF?") is None


def test_impacto_general_no_fuerza_tool_choice() -> None:
    assert _first_choice("¿Qué es el impacto de la diversificación?") is None


def test_agente_recibe_la_fecha_de_hoy(maria) -> None:
    llm = ScriptedLLM(
        [
            AIMessage(
                content="Voy a buscar la noticia.",
                tool_calls=[
                    {
                        "name": "search_news",
                        "args": {"query": "Jensen Huang NVIDIA"},
                        "id": "call-news",
                    }
                ],
            ),
        ],
        final_answer="Respuesta.",
    )
    container = _container(maria)
    container.llm = llm
    graph = build_agent_graph(container)

    _run(
        graph,
        {
            "messages": [HumanMessage(content="¿Me afecta la salida de Jensen Huang?")],
            "user_id": "maria-lopez",
            "query": "¿Me afecta la salida de Jensen Huang?",
            "tool_rounds": 0,
        },
    )

    system = llm.calls[0][0]
    assert "Fecha de hoy:" in system.content
    assert date.today().isoformat() in system.content


class TwoNewsWeb:
    """Returns the resignation first and the return second, out of order."""

    async def search(self, query: str):
        return [
            SimpleNamespace(
                title="Jensen Huang Resigns as Nvidia CEO",
                url="https://www.wired.com/story/renuncia",
                snippet="Nvidia announced a leadership transition.",
                published_at="2026-11-12",
                source="www.wired.com",
            ),
            SimpleNamespace(
                title="Jensen Huang Returns to Nvidia",
                url="https://www.reuters.com/story/regreso",
                snippet="The board reinstated Huang as CEO.",
                published_at="2026-11-17",
                source="www.reuters.com",
            ),
        ]


def test_agente_prioriza_la_noticia_mas_reciente(maria) -> None:
    llm = ScriptedLLM(
        [
            AIMessage(
                content="Voy a buscar la noticia y su estado actual.",
                tool_calls=[
                    {
                        "name": "search_news",
                        "args": {"query": "Jensen Huang NVIDIA"},
                        "id": "call-news",
                    }
                ],
            ),
        ],
        final_answer="Salió el 12 y volvió el 17.",
    )
    container = _container(maria)
    container.web = TwoNewsWeb()
    container.llm = llm
    graph = build_agent_graph(container)

    final, _ = _run(
        graph,
        {
            "messages": [HumanMessage(content="¿Me afecta la salida de Jensen Huang?")],
            "user_id": "maria-lopez",
            "query": "¿Me afecta la salida de Jensen Huang?",
            "tool_rounds": 0,
        },
    )

    web_sources = [item for item in final["sources"] if item["kind"] == "web"]
    assert web_sources[0]["url"] == "https://www.reuters.com/story/regreso"
