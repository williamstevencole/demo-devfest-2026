"""Graph assembly: model ↔ tools, sufficiency check, then the final answer."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.nodes import (
    make_agent_node,
    make_finalize_node,
    make_sufficiency_node,
    make_trace_tools_node,
    route_after_agent,
    route_after_check,
)
from app.agent.state import AgentState
from app.agent.tools.definitions import build_tools


def build_agent_graph(container: Any):
    """Compile the autonomous agent: model ↔ tools, then a final answer."""

    tools = build_tools(container)
    graph = StateGraph(AgentState)
    graph.add_node("agent", make_agent_node(container.llm, tools))
    graph.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    graph.add_node("trace_tools", make_trace_tools_node())
    graph.add_node("check", make_sufficiency_node(container.llm))
    graph.add_node("finalize", make_finalize_node(container.llm))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "check": "check", "finalize": "finalize"},
    )
    graph.add_edge("tools", "trace_tools")
    graph.add_edge("trace_tools", "check")
    graph.add_conditional_edges(
        "check",
        route_after_check,
        {"finalize": "finalize", "agent": "agent"},
    )
    graph.add_edge("finalize", END)
    return graph.compile()
