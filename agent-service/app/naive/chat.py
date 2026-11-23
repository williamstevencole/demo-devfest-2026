"""Honest naive RAG mode: one retrieval and one prompt, no tools."""

import logging
from collections.abc import AsyncIterator
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel

from app.agent.trace import TraceSpan
from app.config import Settings
from app.domain.citations import source_label
from app.domain.intents import classify_question
from app.domain.llm_messages import LLM_ERROR_ANSWER, message_text
from app.domain.response import ChatResult, collect_sources
from app.naive.prompt import build_naive_prompt

logger = logging.getLogger(__name__)

NODE_NAME = "naive"
DETAIL_LIMIT = 200
EXPANDED_TOP_K = 7
WITHDRAWAL_TOP_K = 5
WITHDRAWAL_HINTS = (
    "comisiones spread cambiario retiro comisión de acciones y ETFs comisión de trading"
)
CHIP_HINTS = "tecnología semiconductores volatilidad concentración diversificación"

StreamEvent = tuple[Literal["step", "token", "result"], Any]


def retrieval_request(query: str, top_k: int) -> tuple[str, int]:
    """Add corpus vocabulary for questions the raw wording under-retrieves."""

    intent = classify_question(query)
    hints: list[str] = []
    minimum = top_k
    if intent.asks_withdrawal:
        hints.append(WITHDRAWAL_HINTS)
        minimum = max(minimum, WITHDRAWAL_TOP_K)
    if intent.mentions_chips:
        hints.append(CHIP_HINTS)
        minimum = max(minimum, EXPANDED_TOP_K)
    if not hints:
        return query, top_k
    return f"{query} {' '.join(hints)}", minimum


class NaiveChat:
    """Answer from the local corpus without portfolio, tools or web."""

    def __init__(self, knowledge, llm: BaseChatModel, settings: Settings) -> None:
        self._knowledge = knowledge
        self._llm = llm
        self._settings = settings

    async def run(self, query: str, history: list[dict[str, str]] | None = None) -> ChatResult:
        """Consume the stream and return the final result."""

        result: ChatResult | None = None
        async for kind, payload in self.stream(query, history=history):
            if kind == "result":
                result = payload
        if result is None:
            raise RuntimeError("NaiveChat no produjo una respuesta")
        return result

    async def _stream_llm(self, prompt: str) -> AsyncIterator[Any]:
        """Prefer token streaming and fall back to one-shot calls for fakes."""

        if hasattr(self._llm, "astream"):
            async for chunk in self._llm.astream(prompt):
                yield chunk
            return
        if hasattr(self._llm, "ainvoke"):
            yield await self._llm.ainvoke(prompt)
            return
        yield self._llm.invoke(prompt)

    async def stream(
        self, query: str, history: list[dict[str, str]] | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Emit retrieval and answer steps as they happen, plus answer tokens."""

        search_query, top_k = retrieval_request(query, self._settings.retrieval_top_k)

        pending: list[Any] = []
        trace: list[Any] = []
        retrieval = TraceSpan(
            pending.append,
            NODE_NAME,
            "retrieval",
            "Buscar en el conocimiento del broker",
        )
        yield "step", pending.pop(0)
        documents = self._knowledge.search(search_query, top_k)
        labels = [source_label(document.source, document.section) for document in documents]
        count = (
            f"{len(documents)} documento encontrado"
            if len(documents) == 1
            else (f"{len(documents)} documentos encontrados")
        )
        retrieval_step = retrieval.finish(
            f"Consulta: «{search_query[:120]}» · {count}",
            labels,
        )
        trace.append(retrieval_step)
        yield "step", retrieval_step

        pending = []
        answer_span = TraceSpan(
            pending.append,
            NODE_NAME,
            "answer",
            "Redactar la respuesta",
        )
        yield "step", pending.pop(0)
        parts: list[str] = []
        llm_error = False
        try:
            async for chunk in self._stream_llm(build_naive_prompt(query, documents, history)):
                text = message_text(chunk)
                if not text:
                    continue
                parts.append(text)
                yield "token", text
        except Exception:
            logger.exception("El modelo falló en el modo naive")
            llm_error = True
        answer = "".join(parts).strip()
        if not answer:
            answer = LLM_ERROR_ANSWER
            llm_error = True
        answer_step = answer_span.finish(
            answer[:DETAIL_LIMIT],
            labels,
            status="error" if llm_error else "done",
            title="No se pudo redactar la respuesta" if llm_error else None,
        )
        trace.append(answer_step)
        yield "step", answer_step
        yield "result", ChatResult(
            answer=answer,
            trace=trace,
            sources=collect_sources(documents, []),
            documents=documents,
            llm_error=llm_error,
        )
