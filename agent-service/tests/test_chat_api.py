"""API contract tests for the autonomous agent chat service."""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.domain.models import Portfolio
from app.domain.response import ChatResult, SourceRef
from app.errors import NestUnavailableError
from app.main import create_app
from app.services.chat_service import ChatService

LOAD_STEP = {
    "id": "",
    "node": "agent",
    "kind": "decision",
    "title": "Decisión",
    "detail": "Voy a revisar la noticia y tu exposición.",
    "sources": [],
    "status": "done",
    "duration_ms": 0,
}

TOOL_STEP = {
    "id": "",
    "node": "agent",
    "kind": "tool_call",
    "title": "Escenario",
    "detail": "NVDA · 25.5% del invertido · -20% = $-929.10",
    "sources": [],
    "status": "done",
    "duration_ms": 0,
}

ANSWER_STEP = {
    "id": "",
    "node": "agent",
    "kind": "answer",
    "title": "Respuesta",
    "detail": "NVIDIA es el 25.5% de tu invertido.",
    "sources": [],
    "status": "done",
    "duration_ms": 0,
}

SOURCE = SourceRef(
    kind="web",
    label="Jensen Huang Resigns as Nvidia CEO",
    detail="www.wired.com · 2026-11-12",
    url="https://www.wired.com/story/nvidia-ceo-jensen-huang-steps-down",
)


class FakeGraph:
    def __init__(
        self,
        final_state: dict,
        steps: list[dict] | None = None,
        tokens: list[str] | None = None,
    ) -> None:
        self._final_state = final_state
        self._steps = steps if steps is not None else [LOAD_STEP, TOOL_STEP, ANSWER_STEP]
        self._tokens = tokens
        self.calls: list[dict] = []

    async def astream(self, state: dict, stream_mode):
        self.calls.append({"state": state, "stream_mode": stream_mode})
        for step in self._steps:
            yield "custom", dict(step)
        if self._tokens is not None:
            for token in self._tokens:
                yield "messages", (AIMessage(content=token), {})
        yield "values", self._final_state


class FailingGraph:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def astream(self, state: dict, stream_mode):
        raise self._error
        yield  # pragma: no cover


class FakeNaive:
    async def run(self, query: str) -> ChatResult:
        return ChatResult(
            answer="Un ETF es un fondo cotizado.",
            trace=[
                {
                    "id": "",
                    "node": "naive",
                    "kind": "retrieval",
                    "title": "Conocimiento local",
                    "detail": "1 documentos recuperados",
                    "sources": ["glosario_de_mercado.md > ETF"],
                    "status": "done",
                    "duration_ms": 1,
                },
                {
                    "id": "",
                    "node": "naive",
                    "kind": "answer",
                    "title": "Respuesta naive",
                    "detail": "Un ETF es un fondo cotizado.",
                    "sources": ["glosario_de_mercado.md > ETF"],
                    "status": "done",
                    "duration_ms": 1,
                },
            ],
            sources=[
                SourceRef(
                    kind="document",
                    label="glosario_de_mercado.md > ETF",
                    detail="Un ETF es un fondo cotizado.",
                )
            ],
        )

    async def stream(self, query: str, history=None):
        result = await self.run(query)
        for step in result.trace:
            yield "step", step
        yield "token", result.answer
        yield "result", result


def _service(graph) -> ChatService:
    return ChatService(graph, FakeNaive())


def _client(service: ChatService) -> TestClient:
    app = create_app(
        lambda settings: SimpleNamespace(
            settings=settings,
            nest=SimpleNamespace(),
            chat=service,
        )
    )
    return TestClient(app)


def _maria_state(maria: Portfolio) -> dict:
    return {
        "answer": "NVIDIA es el 25.5% de tu invertido.",
        "sources": [SOURCE.model_dump(mode="json")],
        "trace": [LOAD_STEP, TOOL_STEP, ANSWER_STEP],
        "missing_data": [],
        "disclaimer_required": True,
    }


def test_chat_json_devuelve_traza_y_fuentes(maria: Portfolio) -> None:
    graph = FakeGraph(_maria_state(maria))
    with _client(_service(graph)) as client:
        response = client.post(
            "/api/chat",
            json={
                "user_id": "maria-lopez",
                "query": "¿Me afecta Jensen Huang?",
                "mode": "agent",
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["mode"] == "agent"
    assert [step["kind"] for step in body["trace"]["steps"]] == [
        "decision",
        "tool_call",
        "answer",
    ]
    assert [step["id"] for step in body["trace"]["steps"]] == ["s1", "s2", "s3"]
    assert "analysis" not in body
    assert "withdrawal" not in body
    assert body["sources"][0]["kind"] == "web"
    assert body["disclaimer_required"] is True


def test_historial_se_envia_al_agente_como_mensajes(maria: Portfolio) -> None:
    graph = FakeGraph(_maria_state(maria))
    with _client(_service(graph)) as client:
        response = client.post(
            "/api/chat",
            json={
                "user_id": "maria-lopez",
                "query": "¿Y eso cómo me afecta?",
                "mode": "agent",
                "history": [
                    {"role": "user", "content": "Jensen Huang renunció."},
                    {"role": "assistant", "content": "Es una noticia de NVIDIA."},
                ],
            },
        )

    assert response.status_code == 200
    messages = graph.calls[0]["state"]["messages"]
    assert [message.type for message in messages] == ["human", "ai", "human"]


def test_sse_emite_step_token_y_done(maria: Portfolio) -> None:
    with _client(_service(FakeGraph(_maria_state(maria)))) as client:
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"user_id": "maria-lopez", "query": "x", "mode": "agent"},
        ) as response:
            body = "".join(response.iter_text())

    assert '"type": "step"' in body
    assert '"type": "token"' in body
    assert '"type": "done"' in body
    assert '"kind": "tool_call"' in body


def test_sse_reporta_error_del_modelo_sin_fingir_respuesta() -> None:
    final = {
        "answer": "No pude consultar el modelo en este momento.",
        "sources": [],
        "trace": [],
        "missing_data": [],
        "disclaimer_required": False,
        "llm_error": True,
    }
    with _client(_service(FakeGraph(final))) as client:
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"user_id": "maria-lopez", "query": "x", "mode": "agent"},
        ) as response:
            body = "".join(response.iter_text())

    assert '"type": "error"' in body
    assert '"type": "done"' not in body
    assert "No pude consultar el modelo" in body


def test_nest_caido_responde_503() -> None:
    with _client(_service(FailingGraph(NestUnavailableError("down")))) as client:
        response = client.post(
            "/api/chat",
            json={"user_id": "maria-lopez", "query": "x", "mode": "agent"},
        )

    assert response.status_code == 503
    assert "portafolio" in response.json()["detail"].lower()


def test_error_inesperado_no_filtra_detalles() -> None:
    with _client(_service(FailingGraph(RuntimeError("secret internals")))) as client:
        response = client.post(
            "/api/chat",
            json={"user_id": "maria-lopez", "query": "x", "mode": "agent"},
        )

    assert response.status_code == 500
    assert "secret internals" not in response.json()["detail"]


def test_modo_naive_no_usa_el_agente() -> None:
    graph = FakeGraph({})
    with _client(_service(graph)) as client:
        response = client.post(
            "/api/chat",
            json={"user_id": "maria-lopez", "query": "¿Qué es un ETF?", "mode": "naive"},
        )

    body = response.json()
    assert body["mode"] == "naive"
    assert "analysis" not in body
    assert "withdrawal" not in body
    assert [step["kind"] for step in body["trace"]["steps"]] == [
        "retrieval",
        "answer",
    ]
    assert graph.calls == []


def test_trace_ids_son_unicos(maria: Portfolio) -> None:
    repeated = dict(TOOL_STEP)
    final = {**_maria_state(maria), "trace": [LOAD_STEP, repeated, repeated]}
    with _client(_service(FakeGraph(final))) as client:
        response = client.post(
            "/api/chat",
            json={"user_id": "maria-lopez", "query": "x", "mode": "agent"},
        )

    ids = [step["id"] for step in response.json()["trace"]["steps"]]
    assert len(ids) == len(set(ids))


def test_sse_tokens_concuerdan_con_la_respuesta_final(maria: Portfolio) -> None:
    final = {
        **_maria_state(maria),
        "answer": "Parte uno.\n\nEsta información es educativa y no es asesoría.",
    }
    graph = FakeGraph(final, tokens=["Parte uno."])
    with _client(_service(graph)) as client:
        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"user_id": "maria-lopez", "query": "x", "mode": "agent"},
        ) as response:
            body = "".join(response.iter_text())

    events = [
        __import__("json").loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    tokens = "".join(event["text"] for event in events if event["type"] == "token")
    done = next(event for event in events if event["type"] == "done")
    assert tokens == done["answer"]
