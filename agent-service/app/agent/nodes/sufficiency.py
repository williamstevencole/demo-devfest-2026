"""Sufficiency check node: decides whether the turn has enough data."""

import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompt import SUFFICIENCY_INSTRUCTION, SUFFICIENCY_SYSTEM
from app.agent.schemas import SufficiencyCheck
from app.agent.state import AgentState
from app.agent.trace import emit_step, make_step

logger = logging.getLogger(__name__)

MAX_SUFFICIENCY_CHECKS = 3
SUFFICIENCY_ATTEMPTS = 2

STALE_REASON = "no se verificó el estado actual de un evento que puede haber cambiado"
CONFLICT_REASON = "hay fuentes en conflicto sin resolver"


def _sufficiency_feedback(result: SufficiencyCheck, check_rounds: int, missing: list[str]) -> str:
    """Build the instruction that tells the agent what to look for next."""

    parts = ["La verificación determinó que todavía faltan datos para responder con seguridad."]
    if missing:
        parts.append("Falta: " + "; ".join(missing) + ".")
    if result.next_tool:
        parts.append(f"Vuelve a usar la herramienta {result.next_tool}.")
    if result.next_query:
        parts.append(f"Consulta sugerida: {result.next_query}.")
    if check_rounds >= MAX_SUFFICIENCY_CHECKS:
        parts.append("No quedan verificaciones: responde con lo disponible y di qué falta.")
    else:
        parts.append("Si no puedes obtener esos datos, dilo claramente.")
    return "\n".join(parts)


def make_sufficiency_node(llm: Any, checker: Any | None = None):
    """Build the node that verifies whether the turn has enough data."""

    if checker is None:
        factory = getattr(llm, "with_structured_output", None)
        if factory is not None:
            try:
                checker = factory(SufficiencyCheck)
            except Exception:
                checker = None

    async def check_sufficiency(state: AgentState) -> dict:
        check_rounds = state.get("check_rounds", 0) + 1
        started = time.monotonic()
        failed = checker is None
        if checker is None:
            result = SufficiencyCheck(sufficient=True)
        else:
            messages = [
                SystemMessage(content=SUFFICIENCY_SYSTEM),
                *state.get("messages", []),
                HumanMessage(content=SUFFICIENCY_INSTRUCTION),
            ]
            for attempt in range(1, SUFFICIENCY_ATTEMPTS + 1):
                try:
                    raw = await checker.ainvoke(messages)
                    result = (
                        raw
                        if isinstance(raw, SufficiencyCheck)
                        else SufficiencyCheck.model_validate(raw)
                    )
                    failed = False
                    break
                except Exception:
                    logger.exception(
                        "La verificación de suficiencia falló (intento %s/%s)",
                        attempt,
                        SUFFICIENCY_ATTEMPTS,
                    )
                    failed = True
                    result = SufficiencyCheck(sufficient=True)

        duration = round((time.monotonic() - started) * 1000)
        forced: list[str] = []
        if result.stale_evidence:
            forced.append(STALE_REASON)
        if result.conflict_type == "unresolved":
            forced.append(CONFLICT_REASON)
        sufficient = bool(result.sufficient) and not forced
        missing = (
            []
            if sufficient
            else [str(item).strip() for item in (result.missing or []) if str(item).strip()]
        )
        if not sufficient:
            missing.extend(reason for reason in forced if reason not in missing)
            if not missing:
                missing = ["No hay datos suficientes para responder con seguridad."]
        if failed:
            detail = "No se pudo verificar; se continúa con la respuesta."
        elif sufficient:
            detail = "La información alcanza para responder."
        else:
            detail = "Faltan datos: " + "; ".join(missing) + "."
        step = make_step(
            "decision",
            "Verificar si alcanza la información",
            detail,
            status="error" if failed else "done",
            duration_ms=duration,
        )
        emit_step(step)

        update: dict[str, Any] = {
            "check_rounds": check_rounds,
            "missing_data": missing,
            "trace": [step],
        }
        if not sufficient and check_rounds < MAX_SUFFICIENCY_CHECKS:
            update["messages"] = [
                HumanMessage(content=_sufficiency_feedback(result, check_rounds, missing))
            ]
        return update

    return check_sufficiency


def route_after_check(state: AgentState) -> str:
    """Continue investigating or finish with the data available."""

    if state.get("llm_error"):
        return "finalize"
    if not state.get("missing_data"):
        return "finalize"
    if state.get("check_rounds", 0) >= MAX_SUFFICIENCY_CHECKS:
        return "finalize"
    return "agent"
