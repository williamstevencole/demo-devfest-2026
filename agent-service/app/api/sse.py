"""Server-sent event encoding for the chat trace."""

import json
from dataclasses import dataclass
from typing import Any, Literal

ChatEventType = Literal["step", "token", "done", "error"]


@dataclass
class ChatEvent:
    """One SSE event emitted while a chat answer is produced."""

    type: ChatEventType
    data: dict[str, Any]


def format_sse(event: ChatEvent) -> str:
    """Render a chat event as one SSE data frame."""

    payload = {"type": event.type, **event.data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
