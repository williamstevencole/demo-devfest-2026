"""Trace contract shared by graph nodes, the API and the UI."""

from typing import Literal, TypedDict

TraceKind = Literal["tool_call", "retrieval", "web_search", "decision", "answer"]
TraceStatus = Literal["running", "done", "error"]


class TraceStep(TypedDict):
    """One observable step in the agent trace."""

    id: str
    node: str
    kind: TraceKind
    title: str
    detail: str
    sources: list[str]
    status: TraceStatus
    duration_ms: int
