from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.ingestion.store import RetrievedDoc
from app.naive.chat import NaiveChat

ETFS = [
    RetrievedDoc(
        text="Un ETF es un fondo que cotiza como una acción.",
        source="glosario_de_mercado.md",
        section="ETF",
        score=0.9,
    )
]


class FakeKnowledge:
    def __init__(self, results: list[RetrievedDoc] | None = None) -> None:
        self.calls: list[tuple[str, int]] = []
        self._results = results if results is not None else ETFS

    def search(self, query: str, top_k: int) -> list[RetrievedDoc]:
        self.calls.append((query, top_k))
        return list(self._results)


class FakeLLM:
    def __init__(self, answer: str = "Un ETF es un fondo cotizado.") -> None:
        self._answer = answer
        self.last_prompt = ""

    async def ainvoke(self, prompt: str) -> AIMessage:
        self.last_prompt = prompt
        return AIMessage(content=self._answer)


def settings(**overrides):
    base = {"retrieval_top_k": 4, "chat_model": "gemini-test"}
    return SimpleNamespace(**{**base, **overrides})


async def test_naive_no_usa_portafolio_ni_web() -> None:
    fake_knowledge = FakeKnowledge()
    fake_llm = FakeLLM()

    result = await NaiveChat(fake_knowledge, fake_llm, settings()).run("¿Qué es un ETF?")

    assert [step["kind"] for step in result.trace] == ["retrieval", "answer"]
    assert result.trace[0]["title"] == "Buscar en el conocimiento del broker"
    assert "Consulta:" in result.trace[0]["detail"]
    assert "1 documento encontrado" in result.trace[0]["detail"]
    assert result.trace[1]["title"] == "Redactar la respuesta"
    assert "cash_usd" not in fake_llm.last_prompt.lower()
    assert "portfolio" not in fake_llm.last_prompt.lower()


async def test_naive_devuelve_solo_fuentes_de_documentos() -> None:
    result = await NaiveChat(FakeKnowledge(), FakeLLM(), settings()).run("¿Qué es un ETF?")

    assert [source.kind for source in result.sources] == ["document"]
    assert result.sources[0].label == "glosario_de_mercado.md > ETF"


async def test_naive_usa_el_top_k_configurado() -> None:
    fake_knowledge = FakeKnowledge()

    await NaiveChat(fake_knowledge, FakeLLM(), settings(retrieval_top_k=2)).run("¿Qué es un ETF?")

    assert fake_knowledge.calls == [("¿Qué es un ETF?", 2)]


@pytest.mark.parametrize("query", ["¿Qué es un ETF?", "¿Cuánto cobran por retirar?"])
async def test_naive_no_recibe_user_id(query: str) -> None:
    result = await NaiveChat(FakeKnowledge(), FakeLLM(), settings()).run(query)

    assert result.answer == "Un ETF es un fondo cotizado."


async def test_naive_prompt_incluye_historial() -> None:
    fake_llm = FakeLLM()

    await NaiveChat(FakeKnowledge(), fake_llm, settings()).run(
        "dame ejemplos",
        history=[
            {"role": "user", "content": "¿Qué es un ETF?"},
            {"role": "assistant", "content": "Un ETF es un fondo cotizado."},
        ],
    )

    assert "Conversación reciente" in fake_llm.last_prompt
    assert "¿Qué es un ETF?" in fake_llm.last_prompt


async def test_naive_expande_consulta_de_retiro_para_recuperar_tarifas() -> None:
    fake_knowledge = FakeKnowledge()

    await NaiveChat(fake_knowledge, FakeLLM(), settings()).run(
        "¿Qué es un ETF y cuánto cobran por retirar?"
    )

    query, top_k = fake_knowledge.calls[0]
    assert "spread cambiario" in query
    assert "retiro" in query
    assert top_k == 5


async def test_prompt_naive_pide_cubrir_cada_parte_y_sus_cifras() -> None:
    fake_knowledge = FakeKnowledge()
    fake_llm = FakeLLM()

    await NaiveChat(fake_knowledge, fake_llm, settings()).run(
        "¿Qué es un ETF y cuánto cobran por retirar?"
    )

    assert "Cubre cada parte" in fake_llm.last_prompt
    assert "condiciones" in fake_llm.last_prompt


async def test_naive_expande_consulta_de_chips_para_recuperar_tecnologia() -> None:
    fake_knowledge = FakeKnowledge()

    await NaiveChat(fake_knowledge, FakeLLM(), settings()).run(
        "¿Me afecta que China restrinja la exportación de chips?"
    )

    query, top_k = fake_knowledge.calls[0]
    assert "semiconductores" in query
    assert "volatilidad" in query
    assert top_k >= 7


class FailingLLM:
    async def ainvoke(self, prompt: str) -> AIMessage:
        raise RuntimeError("LLM unavailable")


class EmptyLLM:
    async def ainvoke(self, prompt: str) -> AIMessage:
        return AIMessage(content="")


async def test_naive_reporta_error_si_el_llm_falla() -> None:
    result = await NaiveChat(FakeKnowledge(), FailingLLM(), settings()).run("¿Qué es un ETF?")

    assert "No pude consultar el modelo" in result.answer
    assert result.llm_error is True
    assert [step["kind"] for step in result.trace] == ["retrieval", "answer"]
    assert result.trace[-1]["status"] == "error"


async def test_naive_reporta_error_si_respuesta_vacia() -> None:
    result = await NaiveChat(FakeKnowledge(), EmptyLLM(), settings()).run("¿Qué es un ETF?")

    assert result.llm_error is True


class StreamingLLM:
    def __init__(self, parts: list[str] | None = None) -> None:
        self._parts = parts or ["Un ETF ", "es un fondo cotizado."]
        self.last_prompt = ""

    async def astream(self, prompt: str):
        self.last_prompt = prompt
        for part in self._parts:
            yield AIMessage(content=part)


async def test_naive_emite_pasos_y_tokens_en_orden() -> None:
    chat = NaiveChat(FakeKnowledge(), StreamingLLM(), settings())

    events = [event async for event in chat.stream("¿Qué es un ETF?")]

    sequence = [
        (kind, payload.get("status") if kind == "step" else None) for kind, payload in events
    ]
    assert sequence == [
        ("step", "running"),
        ("step", "done"),
        ("step", "running"),
        ("token", None),
        ("token", None),
        ("step", "done"),
        ("result", None),
    ]
    assert "".join(payload for kind, payload in events if kind == "token") == (
        "Un ETF es un fondo cotizado."
    )
    result = events[-1][1]
    assert result.answer == "Un ETF es un fondo cotizado."
    assert [step["kind"] for step in result.trace] == ["retrieval", "answer"]

    retrieval_ids = {
        payload["id"]
        for kind, payload in events
        if kind == "step" and payload["kind"] == "retrieval"
    }
    answer_ids = {
        payload["id"] for kind, payload in events if kind == "step" and payload["kind"] == "answer"
    }
    assert len(retrieval_ids) == 1
    assert len(answer_ids) == 1
    assert retrieval_ids != answer_ids


async def test_naive_emite_running_antes_de_consultar_el_corpus() -> None:
    class RecordingKnowledge(FakeKnowledge):
        def __init__(self, seen: list[str]) -> None:
            super().__init__()
            self._seen = seen

        def search(self, query: str, top_k: int):
            self._seen.append("search")
            return super().search(query, top_k)

    seen: list[str] = []
    chat = NaiveChat(RecordingKnowledge(seen), StreamingLLM(), settings())

    async for kind, payload in chat.stream("¿Qué es un ETF?"):
        if kind == "step":
            seen.append(payload["status"])

    assert seen[:2] == ["running", "search"]


async def test_naive_traza_incluye_la_busqueda() -> None:
    chat = NaiveChat(FakeKnowledge(), FakeLLM(), settings())

    events = [event async for event in chat.stream("¿Qué es un ETF?")]

    retrieval = next(
        payload
        for kind, payload in events
        if kind == "step" and payload["kind"] == "retrieval" and payload["status"] == "done"
    )
    assert "Consulta:" in retrieval["detail"]
    assert "¿Qué es un ETF?" in retrieval["detail"]
