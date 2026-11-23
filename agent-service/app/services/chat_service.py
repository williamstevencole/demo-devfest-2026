"""Chat runner shared by the JSON and SSE endpoints."""

from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.api.schemas import ChatMode, ChatResponse
from app.api.sse import ChatEvent
from app.errors import ChatServiceError

MAX_HISTORY_MESSAGES = 8
MAX_HISTORY_CHARS = 1200


def _history_messages(history: list[dict[str, str]] | None) -> list[Any]:
    messages: list[Any] = []
    for item in (history or [])[-MAX_HISTORY_MESSAGES:]:
        content = item.get("content", "").strip()
        if not content:
            continue
        text = content[:MAX_HISTORY_CHARS]
        if item.get("role") == "assistant":
            messages.append(AIMessage(content=text))
        else:
            messages.append(HumanMessage(content=text))
    return messages


def _dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for source in sources:
        key = (
            str(source.get("kind", "")),
            str(source.get("url") or source.get("label", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


def _sources_payload(sources) -> list[dict[str, Any]]:
    return [
        source.model_dump(mode="json") if hasattr(source, "model_dump") else source
        for source in sources
    ]


class _StepIds:
    def __init__(self) -> None:
        self._count = 0

    def _next(self) -> str:
        self._count += 1
        return f"s{self._count}"

    def assign(self, step: dict[str, Any]) -> dict[str, Any]:
        if step.get("id"):
            return step
        return {**step, "id": self._next()}

    @staticmethod
    def renumber(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{**step, "id": f"s{index}"} for index, step in enumerate(steps, 1)]


class ChatService:
    """Aggregate the agent or naive stream into the public chat contract."""

    def __init__(self, graph, naive) -> None:
        self._graph = graph
        self._naive = naive

    async def ask(
        self,
        user_id: str,
        query: str,
        mode: ChatMode,
        history: list[dict[str, str]] | None = None,
    ) -> ChatResponse:
        """Consume the stream and return the final JSON response."""

        async for event in self.stream(user_id, query, mode, history):
            if event.type == "done":
                return ChatResponse.model_validate(event.data)
        raise ChatServiceError("El agente no produjo una respuesta")

    async def stream(
        self,
        user_id: str,
        query: str,
        mode: ChatMode,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[ChatEvent]:
        """Run the selected mode and yield step, token and done events."""

        if mode == "naive":
            async for event in self._stream_naive(query, history=history):
                yield event
            return
        async for event in self._stream_agent(user_id, query, history=history):
            yield event

    async def _stream_agent(
        self,
        user_id: str,
        query: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[ChatEvent]:
        ids = _StepIds()
        final_state: dict[str, Any] = {}
        input_state = {
            "messages": [*_history_messages(history), HumanMessage(content=query)],
            "user_id": user_id,
            "query": query,
            "tool_rounds": 0,
            "check_rounds": 0,
            "trace": [],
            "sources": [],
        }
        async for mode_name, chunk in self._graph.astream(
            input_state, stream_mode=["custom", "values"]
        ):
            if mode_name == "custom" and isinstance(chunk, dict) and chunk.get("kind"):
                yield ChatEvent("step", ids.assign(chunk))
            elif mode_name == "values":
                final_state = chunk
        async for event in self._finish_agent(final_state):
            yield event

    async def _finish_agent(self, final_state: dict[str, Any]) -> AsyncIterator[ChatEvent]:
        answer = final_state.get("answer", "")
        if not answer:
            raise ChatServiceError("El agente no produjo una respuesta")
        if final_state.get("llm_error"):
            yield ChatEvent("error", {"message": answer})
            return
        yield ChatEvent("token", {"text": answer})
        sources = _dedupe_sources(final_state.get("sources", []))
        trace = _StepIds.renumber(final_state.get("trace", []))
        missing_data = list(final_state.get("missing_data", []))
        payload = {
            "answer": answer,
            "mode": "agent",
            "trace": {"steps": trace},
            "sources": _sources_payload(sources),
            "insufficient_data": bool(missing_data),
            "missing_data": missing_data,
            "disclaimer_required": bool(final_state.get("disclaimer_required", False)),
        }
        yield ChatEvent("done", payload)

    async def _stream_naive(
        self,
        query: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[ChatEvent]:
        ids = _StepIds()
        steps: list[dict[str, Any]] = []
        result = None

        async for kind, payload in self._naive.stream(query, history=history):
            if kind == "step":
                step = ids.assign(payload)
                yield ChatEvent("step", step)
                if step["status"] != "running":
                    steps.append(step)
            elif kind == "token":
                yield ChatEvent("token", {"text": payload})
            elif kind == "result":
                result = payload

        if result is None:
            raise ChatServiceError("El modo naive no produjo una respuesta")
        if result.llm_error:
            yield ChatEvent("error", {"message": result.answer})
            return

        payload = {
            "answer": result.answer,
            "mode": "naive",
            "trace": {"steps": _StepIds.renumber(steps)},
            "sources": _sources_payload(result.sources),
            "insufficient_data": False,
            "missing_data": [],
            "disclaimer_required": False,
        }
        yield ChatEvent("done", payload)
