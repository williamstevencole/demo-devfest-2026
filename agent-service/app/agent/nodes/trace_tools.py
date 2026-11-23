"""Tool results node: emits trace steps and collects structured data."""

import json
import time
from typing import Any

from langchain_core.messages import ToolMessage

from app.agent.state import AgentState
from app.agent.tools import payloads as data
from app.agent.trace import DETAIL_LIMIT, emit_step, make_step
from app.domain.trace import TraceStep

TOOL_META = {
    "search_knowledge": ("retrieval", "Buscar en el conocimiento del broker"),
    "search_news": ("web_search", "Buscar noticias"),
    "analyze_portfolio": ("tool_call", "Revisar tu portafolio"),
    "estimate_withdrawal": ("tool_call", "Calcular el retiro"),
    "simulate_sale": ("tool_call", "Simular la venta"),
    "scenario_impact": ("tool_call", "Calcular el impacto"),
}

DISCLAIMER_TOOLS = {
    "analyze_portfolio",
    "estimate_withdrawal",
    "simulate_sale",
    "scenario_impact",
}


def _parse_tool_message(message: ToolMessage) -> dict[str, Any]:
    content = message.content
    if isinstance(content, str):
        try:
            value = json.loads(content)
        except ValueError:
            # ToolNode's fallback handler returns plain text; treat it as an error.
            return {"error": content}
        return value if isinstance(value, dict) else {"value": value}
    return {"value": content}


def _counted(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _tool_detail(name: str, payload: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Return kind, detail and source labels for one tool result."""

    kind, _ = TOOL_META.get(name, ("tool_call", name))
    if payload.get("error"):
        return kind, str(payload["error"]), []

    query = payload.get("query", "")
    if name == "search_knowledge":
        documents = payload.get("documents", [])
        labels = [f"{doc['source']} > {doc['section']}" for doc in documents]
        found = _counted(
            len(documents),
            "documento encontrado",
            "documentos encontrados",
        )
        detail = f"Consulta: «{query}» · {found}"
        return kind, detail, labels
    if name == "search_news":
        results = payload.get("results", [])
        dates = sorted(
            {result.get("published_at") for result in results if result.get("published_at")}
        )
        detail = f"Consulta: «{query}» · {_counted(len(results), 'fuente', 'fuentes')}"
        if dates:
            detail = f"{detail} · {', '.join(dates)}"
        return (
            kind,
            detail,
            [result.get("url") or result.get("title", "") for result in results],
        )
    if name == "analyze_portfolio":
        analysis = payload.get("data", {})
        return (
            kind,
            f"{payload.get('user', 'Portafolio')} · "
            f"{len(analysis.get('positions', []))} posiciones · "
            f"${analysis.get('total_value_usd', 0):,.2f}",
            [],
        )
    if name == "estimate_withdrawal":
        estimate = payload.get("data", {})
        citation = payload.get("citation", {})
        labels = (
            [f"{citation['source']} > {citation['section']}"]
            if citation.get("source") and citation.get("section")
            else []
        )
        return (
            kind,
            f"${estimate.get('amount_usd', 0):,.2f} · "
            f"neto ${estimate.get('net_amount_usd', 0):,.2f} · "
            f"spread ${estimate.get('fx_spread_usd', 0):,.2f}",
            labels,
        )
    if name == "simulate_sale":
        analysis = payload.get("data", {})
        return (
            kind,
            f"{payload.get('impact', {}).get('ticker', 'Venta')} · "
            f"efectivo ${analysis.get('cash_usd', 0):,.2f} · "
            f"invertido ${analysis.get('invested_usd', 0):,.2f}",
            [],
        )
    if name == "scenario_impact":
        exposure = payload.get("exposure", {})
        scenarios = payload.get("scenarios", [])
        ordered = " · ".join(
            f"{item.get('move_pct', 0):+.0f}% = ${item.get('impact_usd', 0):,.2f}"
            for item in scenarios
        )
        return (
            kind,
            f"{payload.get('target', '')} · "
            f"{exposure.get('weight_invested_pct', 0)}% del invertido · {ordered}",
            [],
        )
    return kind, json.dumps(payload, ensure_ascii=False)[:DETAIL_LIMIT], []


def make_trace_tools_node():
    """Emit trace steps and collect structured results from tool messages."""

    async def trace_tools(state: AgentState) -> dict:
        messages = state.get("messages", [])
        new_messages: list[ToolMessage] = []
        for message in reversed(messages):
            if isinstance(message, ToolMessage):
                new_messages.append(message)
            else:
                break
        new_messages.reverse()

        elapsed = round((time.monotonic() - state.get("tool_started_at", time.monotonic())) * 1000)
        updates: dict[str, Any] = {"tool_rounds": state.get("tool_rounds", 0) + 1}
        trace: list[TraceStep] = []
        sources: list[dict[str, Any]] = []
        for message in new_messages:
            name = message.name or "tool"
            payload = _parse_tool_message(message)
            kind, detail, labels = _tool_detail(name, payload)
            status = "error" if payload.get("error") else "done"
            step = make_step(
                kind,
                TOOL_META.get(name, ("tool_call", name))[1],
                detail,
                labels,
                status,
                duration_ms=elapsed,
            )
            emit_step(step)
            trace.append(step)

            extracted = data.sources_from_payload(payload)
            sources.extend(extracted)
            if name in DISCLAIMER_TOOLS:
                updates["disclaimer_required"] = True

        return {**updates, "trace": trace, "sources": sources}

    return trace_tools
