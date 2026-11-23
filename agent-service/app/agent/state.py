"""State shared by the autonomous agent graph."""

import operator
from typing import Annotated, Any

from langgraph.graph import MessagesState

from app.domain.trace import TraceStep


class AgentState(MessagesState, total=False):
    """Conversation, tool results and trace for one agent turn.

    ``MessagesState`` already provides ``messages`` with the ``add_messages``
    reducer, so this class only declares the fields specific to the demo.
    """

    user_id: str
    query: str
    tool_rounds: int
    check_rounds: int
    tool_started_at: float
    trace: Annotated[list[TraceStep], operator.add]
    sources: Annotated[list[dict[str, Any]], operator.add]
    missing_data: list[str]
    llm_error: bool
    answer: str
    disclaimer_required: bool
