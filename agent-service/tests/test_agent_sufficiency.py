"""Tests for the sufficiency check node and its routing."""

import asyncio
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.graph import build_agent_graph
from app.agent.nodes import (
    MAX_SUFFICIENCY_CHECKS,
    MAX_TOOL_ROUNDS,
    make_finalize_node,
    make_sufficiency_node,
    route_after_agent,
    route_after_check,
)
from app.agent.prompt import INSUFFICIENT_ANSWER_INSTRUCTION
from app.agent.schemas import SufficiencyCheck
from app.api.schemas import ChatResponse
from app.domain.llm_messages import LLM_ERROR_ANSWER
from app.services.chat_service import ChatService


class FakeChecker:
    def __init__(self, results) -> None:
        self.results = list(results)
        self.calls: list[list] = []

    async def ainvoke(self, messages):
        self.calls.append(list(messages))
        value = self.results.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def _state(**overrides):
    state = {
        "messages": [HumanMessage(content="¿Qué es un ETF?")],
        "query": "¿Qué es un ETF?",
        "check_rounds": 0,
    }
    state.update(overrides)
    return state


def _run(graph, state):
    async def collect():
        values = None
        async for mode, chunk in graph.astream(state, stream_mode=["custom", "values"]):
            if mode == "values":
                values = chunk
        return values

    return asyncio.run(collect())


def test_check_suficiente_rutea_a_finalize() -> None:
    node = make_sufficiency_node(None, checker=FakeChecker([SufficiencyCheck(sufficient=True)]))

    update = asyncio.run(node(_state()))

    assert update["missing_data"] == []
    assert update["check_rounds"] == 1
    assert "messages" not in update
    assert update["trace"][0]["title"] == "Verificar si alcanza la información"
    assert route_after_check(update) == "finalize"


def test_check_insuficiente_devuelve_feedback_y_rutea_a_agent() -> None:
    result = SufficiencyCheck(
        sufficient=False,
        missing=["noticia reciente sobre NVIDIA"],
        next_query="NVIDIA noticias últimos 7 días",
        next_tool="search_news",
    )
    node = make_sufficiency_node(None, checker=FakeChecker([result]))

    update = asyncio.run(node(_state()))

    assert update["check_rounds"] == 1
    assert update["missing_data"] == ["noticia reciente sobre NVIDIA"]
    assert route_after_check(update) == "agent"

    feedback = update["messages"][0].content
    assert "noticia reciente sobre NVIDIA" in feedback
    assert "search_news" in feedback
    assert "NVIDIA noticias últimos 7 días" in feedback


def test_check_insuficiente_al_agotar_presupuesto_rutea_a_finalize() -> None:
    result = SufficiencyCheck(sufficient=False, missing=["un dato que no existe"])
    node = make_sufficiency_node(None, checker=FakeChecker([result]))

    update = asyncio.run(node(_state(check_rounds=MAX_SUFFICIENCY_CHECKS - 1)))

    assert update["check_rounds"] == MAX_SUFFICIENCY_CHECKS
    assert update["missing_data"] == ["un dato que no existe"]
    assert route_after_check(update) == "finalize"


def test_check_que_falla_es_fail_open() -> None:
    node = make_sufficiency_node(
        None,
        checker=FakeChecker([RuntimeError("cuota agotada"), RuntimeError("cuota agotada")]),
    )

    update = asyncio.run(node(_state()))

    assert update["missing_data"] == []
    assert route_after_check(update) == "finalize"
    assert update["trace"][0]["status"] == "error"


def test_verificador_reintenta_una_vez_si_falla() -> None:
    result = SufficiencyCheck(sufficient=False, missing=["el estado actual del evento"])
    checker = FakeChecker([RuntimeError("429"), result])
    node = make_sufficiency_node(None, checker=checker)

    update = asyncio.run(node(_state()))

    assert len(checker.calls) == 2
    assert update["missing_data"] == ["el estado actual del evento"]
    assert update["trace"][0]["status"] == "done"
    assert route_after_check(update) == "agent"


def test_route_after_agent_manda_sin_tools_al_check() -> None:
    assert route_after_agent({"messages": [AIMessage(content="Hola")], "tool_rounds": 0}) == "check"
    assert (
        route_after_agent(
            {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[{"name": "search_news", "args": {"query": "x"}, "id": "1"}],
                    )
                ],
                "tool_rounds": 0,
            }
        )
        == "tools"
    )
    assert (
        route_after_agent(
            {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[{"name": "search_news", "args": {"query": "x"}, "id": "1"}],
                    )
                ],
                "tool_rounds": MAX_TOOL_ROUNDS,
            }
        )
        == "check"
    )


class RecordingLLM:
    def __init__(self) -> None:
        self.messages: list | None = None

    async def ainvoke(self, messages):
        self.messages = list(messages)
        return AIMessage(content="No tengo información suficiente para responder.")


def test_finalize_usa_instruccion_de_datos_insuficientes() -> None:
    llm = RecordingLLM()
    node = make_finalize_node(llm)
    result = asyncio.run(
        node(
            {
                "messages": [HumanMessage(content="¿Cuánto cuesta?")],
                "missing_data": ["la comisión exacta"],
            }
        )
    )

    assert result["missing_data"] == ["la comisión exacta"]
    assert llm.messages[-1].content == INSUFFICIENT_ANSWER_INSTRUCTION


class FlakyComposerLLM:
    """Fails the first N compose calls, then answers."""

    def __init__(self, failures: int, answer: str = "Respuesta recuperada.") -> None:
        self.failures = failures
        self.answer = answer
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("429 quota exceeded")
        return AIMessage(content=self.answer)


class EmptyThenTextLLM:
    """Returns an empty compose response once, then text."""

    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        return AIMessage(content="" if self.calls == 1 else "Listo.")


def test_finalize_reintenta_si_el_modelo_falla() -> None:
    llm = FlakyComposerLLM(failures=1)
    node = make_finalize_node(llm)

    result = asyncio.run(
        node({"messages": [HumanMessage(content="¿Me afecta Jensen Huang?")], "missing_data": []})
    )

    assert llm.calls == 2
    assert result["answer"] == "Respuesta recuperada."
    assert result["llm_error"] is False


def test_finalize_reintenta_si_la_respuesta_viene_vacia() -> None:
    llm = EmptyThenTextLLM()
    node = make_finalize_node(llm)

    result = asyncio.run(
        node({"messages": [HumanMessage(content="¿Me afecta?")], "missing_data": []})
    )

    assert llm.calls == 2
    assert result["answer"] == "Listo."


def test_finalize_marca_error_si_no_puede_redactar() -> None:
    llm = FlakyComposerLLM(failures=2)
    node = make_finalize_node(llm)

    result = asyncio.run(
        node({"messages": [HumanMessage(content="¿Me afecta?")], "missing_data": []})
    )

    assert llm.calls == 2
    assert result["llm_error"] is True
    assert result["answer"] == LLM_ERROR_ANSWER


def test_chat_response_expone_datos_insuficientes() -> None:
    response = ChatResponse.model_validate(
        {
            "answer": "No tengo información suficiente.",
            "mode": "agent",
            "trace": {"steps": []},
            "insufficient_data": True,
            "missing_data": ["noticia reciente"],
        }
    )

    assert response.insufficient_data is True
    assert response.missing_data == ["noticia reciente"]


class _FakeGraph:
    async def astream(self, state, stream_mode):
        yield "values", {
            "answer": "No tengo información suficiente.",
            "missing_data": ["noticia reciente"],
            "sources": [],
            "trace": [],
        }


def test_chat_service_incluye_bandera_en_el_evento_done() -> None:
    service = ChatService(_FakeGraph(), None)

    async def collect():
        return [event async for event in service.stream("u", "q", "agent")]

    events = asyncio.run(collect())
    done = next(event for event in events if event.type == "done")

    assert done.data["insufficient_data"] is True
    assert done.data["missing_data"] == ["noticia reciente"]


class ToolThenFailLLM:
    """Calls a tool, then fails when the composer tries to write the answer."""

    def bind_tools(self, tools, tool_choice=None):
        return self

    async def ainvoke(self, messages):
        if any(isinstance(message, ToolMessage) for message in messages):
            raise RuntimeError("429 quota exceeded")
        return AIMessage(
            content="Voy a revisar tu portafolio.",
            tool_calls=[
                {"name": "analyze_portfolio", "args": {}, "id": "call-portfolio"},
            ],
        )


class StubKnowledge:
    def search(self, query: str, top_k: int):
        return [
            SimpleNamespace(
                text="Un ETF es un fondo que se negocia en bolsa.",
                source="glosario_de_mercado.md",
                section="ETF",
                score=0.9,
            )
        ]


class StructuredLLM:
    def __init__(self, checker, responses, final_answer="Un ETF es un fondo cotizado.") -> None:
        self._checker = checker
        self._responses = list(responses)
        self._final_answer = final_answer
        self.calls: list[list] = []

    def bind_tools(self, tools, tool_choice=None):
        return self

    def with_structured_output(self, schema):
        return self._checker

    async def ainvoke(self, messages):
        self.calls.append(list(messages))
        if self._responses:
            return self._responses.pop(0)
        return AIMessage(content=self._final_answer)


def test_grafo_completo_reintenta_tras_check_insuficiente() -> None:
    checker = FakeChecker(
        [
            SufficiencyCheck(
                sufficient=False,
                missing=["más detalle del glosario"],
                next_query="ETF definición y características",
                next_tool="search_knowledge",
            ),
            SufficiencyCheck(sufficient=True),
        ]
    )
    llm = StructuredLLM(
        checker,
        [
            AIMessage(
                content="Voy a buscar en el glosario.",
                tool_calls=[
                    {
                        "name": "search_knowledge",
                        "args": {"query": "qué es un ETF"},
                        "id": "call-knowledge",
                    }
                ],
            )
        ],
    )
    container = SimpleNamespace(
        nest=None,
        knowledge=StubKnowledge(),
        web=None,
        llm=llm,
        settings=SimpleNamespace(retrieval_top_k=4),
    )
    graph = build_agent_graph(container)

    final = _run(
        graph,
        {
            "messages": [HumanMessage(content="¿Qué es un ETF?")],
            "user_id": "",
            "query": "¿Qué es un ETF?",
            "tool_rounds": 0,
            "check_rounds": 0,
        },
    )

    assert final["check_rounds"] == 2
    assert final["missing_data"] == []
    assert final["answer"] == "Un ETF es un fondo cotizado."
    assert any(
        isinstance(message, HumanMessage) and "más detalle del glosario" in message.content
        for message in final["messages"]
    )


class StubNest:
    def __init__(self, portfolio) -> None:
        self._portfolio = portfolio

    async def get_portfolio(self, user_id: str):
        if self._portfolio is None or self._portfolio.user.id != user_id:
            return None
        return self._portfolio


def test_finalize_no_filtra_json_de_la_tool_si_falla_el_modelo(maria) -> None:
    container = SimpleNamespace(
        nest=StubNest(maria),
        knowledge=None,
        web=None,
        llm=ToolThenFailLLM(),
        settings=SimpleNamespace(retrieval_top_k=4),
    )
    graph = build_agent_graph(container)

    final = _run(
        graph,
        {
            "messages": [HumanMessage(content="Analiza mi portafolio")],
            "user_id": "maria-lopez",
            "query": "Analiza mi portafolio",
            "tool_rounds": 0,
            "check_rounds": 0,
        },
    )

    assert not final["answer"].lstrip().startswith("{")
    assert final["answer"] == LLM_ERROR_ANSWER
    assert final["llm_error"] is True


def test_evidencia_desactualizada_fuerza_reintento() -> None:
    result = SufficiencyCheck(sufficient=True, stale_evidence=True)
    node = make_sufficiency_node(None, checker=FakeChecker([result]))

    update = asyncio.run(node(_state()))

    assert route_after_check(update) == "agent"
    assert any("actual" in item for item in update["missing_data"])
    feedback = update["messages"][0].content
    assert "estado actual" in feedback


def test_conflicto_sin_resolver_fuerza_reintento() -> None:
    result = SufficiencyCheck(sufficient=True, conflict_type="unresolved")
    node = make_sufficiency_node(None, checker=FakeChecker([result]))

    update = asyncio.run(node(_state()))

    assert route_after_check(update) == "agent"
    assert any("conflicto" in item.lower() for item in update["missing_data"])


def test_conflicto_desactualizado_ya_resuelto_no_fuerza_reintento() -> None:
    result = SufficiencyCheck(sufficient=True, conflict_type="outdated")
    node = make_sufficiency_node(None, checker=FakeChecker([result]))

    update = asyncio.run(node(_state()))

    assert update["missing_data"] == []
    assert route_after_check(update) == "finalize"


def test_presupuesto_permite_tres_verificaciones() -> None:
    assert MAX_SUFFICIENCY_CHECKS == 3
