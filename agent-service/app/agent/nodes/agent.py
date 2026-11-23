"""Model node: decides which tools to call or writes the answer."""

import logging
import re
import time
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agent.prompt import build_system_prompt
from app.agent.state import AgentState
from app.agent.trace import emit_step, make_step
from app.domain.llm_messages import LLM_ERROR_ANSWER, message_text
from app.domain.trace import TraceStep

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 4

TOOL_ACTIONS = {
    "search_knowledge": "buscar en el conocimiento del broker",
    "search_news": "buscar noticias",
    "analyze_portfolio": "revisar tu portafolio",
    "estimate_withdrawal": "calcular el retiro",
    "simulate_sale": "simular la venta",
    "scenario_impact": "calcular el impacto",
}
GENERIC_DECISION = "El modelo decidió qué consultar en esta ronda."
TITLE_QUERY_LIMIT = 60
PERSONAL_QUERY = re.compile(
    r"\b(mi|mis|me|tengo|puedo|deber[ií]a|recomiend\w*|vendo|vender|compro|comprar)\b",
    re.IGNORECASE,
)


def _needs_personal_data(query: str) -> bool:
    """Detect questions that must be grounded in fresh portfolio data."""

    text = query.strip()
    return "y si" in text.lower() or PERSONAL_QUERY.search(text) is not None


def _call_action(call: dict[str, Any]) -> str:
    """Describe one tool call in plain language, including its target."""

    name = call.get("name", "")
    args = call.get("args") or {}
    action = TOOL_ACTIONS.get(name, name)
    query = str(args.get("query") or "").strip()
    if query and name in {"search_knowledge", "search_news"}:
        return f"{action}: «{query[:TITLE_QUERY_LIMIT]}»"
    amount = args.get("amount_usd")
    if name == "estimate_withdrawal" and isinstance(amount, int | float):
        return f"{action} de ${amount:,.2f}"
    target = str(args.get("ticker") or args.get("target") or "").strip()
    if target and name in {"simulate_sale", "scenario_impact"}:
        return f"{action} de {target}"
    return action


def _decision_title(response: Any) -> str:
    """Name the action the agent is about to take."""

    actions: list[str] = []
    for call in getattr(response, "tool_calls", None) or []:
        action = _call_action(call)
        if action and action not in actions:
            actions.append(action)
    if not actions:
        return "Decidir la respuesta"
    if len(actions) == 1:
        title = actions[0]
    else:
        title = f"{', '.join(actions[:-1])} y {actions[-1]}"
    return title[:1].upper() + title[1:]


def _decision_detail(response: Any) -> str:
    """Keep a specific model phrase, or explain that it chose tools."""

    text = message_text(response).strip()
    if text and "herramienta" not in text.lower():
        return text
    return GENERIC_DECISION


def make_agent_node(llm: Any, tools: Sequence[BaseTool]):
    """Build the model node that decides which tools to call."""

    bound = llm.bind_tools(tools)
    try:
        bound_required = llm.bind_tools(tools, tool_choice="any")
    except TypeError:
        bound_required = None

    async def agent(state: AgentState) -> dict:
        messages = [SystemMessage(content=build_system_prompt()), *state.get("messages", [])]
        started = time.monotonic()
        llm_error = False
        force_tools = (
            bound_required is not None
            and state.get("tool_rounds", 0) == 0
            and _needs_personal_data(state.get("query", ""))
        )
        model = bound_required if force_tools else bound
        try:
            response = await model.ainvoke(messages)
        except Exception:
            logger.exception("El modelo falló al decidir la siguiente acción")
            response = AIMessage(content=LLM_ERROR_ANSWER)
            llm_error = True
        duration = round((time.monotonic() - started) * 1000)
        trace: list[TraceStep] = []
        if getattr(response, "tool_calls", None):
            title = _decision_title(response)
            detail = _decision_detail(response)
            step = make_step("decision", title, detail, duration_ms=duration)
            emit_step(step)
            trace.append(step)
        update: dict[str, Any] = {"messages": [response], "trace": trace}
        if llm_error:
            update["llm_error"] = True
        if getattr(response, "tool_calls", None):
            update["tool_started_at"] = time.monotonic()
        return update

    return agent


def route_after_agent(state: AgentState) -> str:
    """Stop immediately when the model failed, otherwise continue the loop."""

    if state.get("llm_error"):
        return "finalize"
    last = state.get("messages", [])[-1] if state.get("messages") else None
    if getattr(last, "tool_calls", None) and state.get("tool_rounds", 0) < MAX_TOOL_ROUNDS:
        return "tools"
    return "check"
