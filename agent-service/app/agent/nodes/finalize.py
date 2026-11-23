"""Final node: composes the answer and applies grounding guards."""

import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.grounding import (
    allowed_sections_from_messages,
    allowed_urls_from_messages,
    fix_malformed_percentages,
    strip_tool_citations,
    strip_unknown_sections,
    strip_unknown_urls,
)
from app.agent.prompt import (
    ANSWER_INSTRUCTION,
    INSUFFICIENT_ANSWER_INSTRUCTION,
    build_system_prompt,
)
from app.agent.state import AgentState
from app.agent.trace import emit_step, make_step
from app.domain.intents import classify_question
from app.domain.llm_messages import LLM_ERROR_ANSWER, message_text

logger = logging.getLogger(__name__)

FALLBACK_ANSWER = (
    "No pude completar la consulta con la información disponible. "
    "¿Puedes reformular la pregunta o indicar qué dato necesitas?"
)
INSUFFICIENT_FALLBACK = "No tengo información suficiente para responder con seguridad."
COMPOSE_ATTEMPTS = 2


def make_finalize_node(llm: Any):
    """Use the agent's last message as the answer, or force one final reply."""

    async def finalize(state: AgentState) -> dict:
        messages = state.get("messages", [])
        last = messages[-1] if messages else None
        missing_data = state.get("missing_data", [])
        insufficient = bool(missing_data)
        if state.get("llm_error"):
            return {
                "answer": message_text(last) or LLM_ERROR_ANSWER,
                "disclaimer_required": False,
                "missing_data": missing_data,
                "llm_error": True,
                "trace": [],
            }
        answer = ""
        composer_failed = False
        started = time.monotonic()
        instruction = INSUFFICIENT_ANSWER_INSTRUCTION if insufficient else ANSWER_INSTRUCTION
        for attempt in range(1, COMPOSE_ATTEMPTS + 1):
            try:
                response = await llm.ainvoke(
                    [
                        SystemMessage(content=build_system_prompt()),
                        *messages,
                        HumanMessage(content=instruction),
                    ]
                )
                answer = message_text(response).strip()
                if answer:
                    composer_failed = False
                    break
                logger.warning(
                    "El modelo devolvió una respuesta vacía (intento %s/%s)",
                    attempt,
                    COMPOSE_ATTEMPTS,
                )
            except Exception:
                logger.exception(
                    "El modelo falló al redactar la respuesta final (intento %s/%s)",
                    attempt,
                    COMPOSE_ATTEMPTS,
                )
            composer_failed = True
        duration = round((time.monotonic() - started) * 1000)
        if not answer:
            if insufficient:
                answer = INSUFFICIENT_FALLBACK
                if missing_data:
                    answer = f"{answer} Falta: {'; '.join(missing_data)}."
            elif messages:
                answer = LLM_ERROR_ANSWER
            else:
                answer = FALLBACK_ANSWER
        llm_error = composer_failed and not insufficient
        if answer == LLM_ERROR_ANSWER:
            llm_error = True
        answer = strip_unknown_sections(answer, allowed_sections_from_messages(messages))
        answer = strip_unknown_urls(answer, allowed_urls_from_messages(messages))
        answer = strip_tool_citations(answer)
        answer = fix_malformed_percentages(answer)

        sources = state.get("sources", [])
        labels = [source.get("label", "") for source in sources if source.get("label")]
        step = make_step(
            "answer",
            "No se pudo redactar la respuesta" if llm_error else "Redactar la respuesta",
            answer,
            labels,
            status="error" if llm_error else "done",
            duration_ms=duration,
        )
        emit_step(step)
        disclaimer = bool(
            state.get("disclaimer_required", False)
            or classify_question(state.get("query", "")).requests_recommendation
        )
        return {
            "answer": answer,
            "disclaimer_required": disclaimer,
            "missing_data": missing_data,
            "llm_error": llm_error,
            "trace": [step],
        }

    return finalize
