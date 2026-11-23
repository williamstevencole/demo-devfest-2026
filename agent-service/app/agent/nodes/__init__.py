"""Graph nodes, grouped by responsibility.

Every node module exposes a ``make_*_node`` builder with the same shape, so the
graph assembly only has to wire them together.
"""

from app.agent.nodes.agent import MAX_TOOL_ROUNDS, make_agent_node, route_after_agent
from app.agent.nodes.finalize import (
    FALLBACK_ANSWER,
    INSUFFICIENT_FALLBACK,
    make_finalize_node,
)
from app.agent.nodes.sufficiency import (
    MAX_SUFFICIENCY_CHECKS,
    make_sufficiency_node,
    route_after_check,
)
from app.agent.nodes.trace_tools import TOOL_META, make_trace_tools_node

__all__ = [
    "FALLBACK_ANSWER",
    "INSUFFICIENT_FALLBACK",
    "MAX_SUFFICIENCY_CHECKS",
    "MAX_TOOL_ROUNDS",
    "TOOL_META",
    "make_agent_node",
    "make_finalize_node",
    "make_sufficiency_node",
    "make_trace_tools_node",
    "route_after_agent",
    "route_after_check",
]
