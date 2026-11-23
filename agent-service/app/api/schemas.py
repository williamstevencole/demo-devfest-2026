"""Request and response schemas for the chat API."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.response import SourceRef

ChatMode = Literal["agent", "naive"]


class HistoryMessage(BaseModel):
    """One previous turn sent by the UI for conversational context."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    """Body shared by the JSON and SSE chat endpoints."""

    user_id: str = ""
    query: str = Field(min_length=1)
    mode: ChatMode = "agent"
    history: list[HistoryMessage] = Field(default_factory=list)


class TracePayload(BaseModel):
    """Trace envelope expected by the UI."""

    steps: list[dict[str, Any]]


class ChatResponse(BaseModel):
    """Complete chat answer returned by the JSON endpoint."""

    answer: str
    mode: ChatMode
    trace: TracePayload
    sources: list[SourceRef] = Field(default_factory=list)
    insufficient_data: bool = False
    missing_data: list[str] = Field(default_factory=list)
    disclaimer_required: bool = False
