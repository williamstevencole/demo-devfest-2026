"""Trace span helper that emits running and done events."""

import time
from collections.abc import Callable, Sequence
from itertools import count

from langgraph.config import get_stream_writer

from app.domain.trace import TraceKind, TraceStatus, TraceStep

DETAIL_LIMIT = 200

Emit = Callable[[TraceStep], None]
Clock = Callable[[], float]
_SPAN_IDS = count(1)


def _stream_emit(payload: TraceStep) -> None:
    try:
        writer = get_stream_writer()
    except RuntimeError:
        return
    writer(payload)


def make_step(
    kind: TraceKind,
    title: str,
    detail: str,
    sources: Sequence[str] | None = None,
    status: TraceStatus = "done",
    duration_ms: int = 0,
) -> TraceStep:
    """Build a trace step with the shared detail limit."""

    return TraceStep(
        id="",
        node="agent",
        kind=kind,
        title=title,
        detail=detail[:DETAIL_LIMIT],
        sources=list(sources or []),
        status=status,
        duration_ms=duration_ms,
    )


def emit_step(step: TraceStep) -> None:
    """Emit a trace step through the LangGraph custom stream, if available."""

    _stream_emit(step)


class TraceSpan:
    """Emit a running step and a completed step with its duration."""

    def __init__(
        self,
        emit: Emit | None,
        node: str,
        kind: TraceKind,
        title: str,
        clock: Clock = time.monotonic,
    ) -> None:
        self._emit = emit or _stream_emit
        self._node = node
        self._kind = kind
        self._title = title
        self._clock = clock
        self._id = f"span-{next(_SPAN_IDS)}"
        self._start = clock()
        self._emit(self._step("running", "", [], 0))

    def _step(
        self,
        status: TraceStatus,
        detail: str,
        sources: list[str],
        duration_ms: int,
    ) -> TraceStep:
        return TraceStep(
            id=self._id,
            node=self._node,
            kind=self._kind,
            title=self._title,
            detail=detail,
            sources=sources,
            status=status,
            duration_ms=duration_ms,
        )

    def finish(
        self,
        detail: str,
        sources: list[str] | None = None,
        status: TraceStatus = "done",
        title: str | None = None,
    ) -> TraceStep:
        """Emit and return the completed step."""

        duration_ms = round((self._clock() - self._start) * 1000)
        step = self._step(status, detail, sources or [], duration_ms)
        if title is not None:
            step = {**step, "title": title}
        self._emit(step)
        return step
