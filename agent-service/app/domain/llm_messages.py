"""Helpers for extracting text from LangChain messages."""

from typing import Any


def message_text(message: Any) -> str:
    """Return the plain text of a chat message, or an empty string."""

    if message is None:
        return ""
    content = getattr(message, "content", None)
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block) for block in content
        )
    return str(content)


LLM_ERROR_ANSWER = (
    "No pude consultar el modelo en este momento. Puede ser un límite temporal "
    "de cuota (plan gratuito) o un problema de conexión. Espera un minuto y "
    "vuelve a intentar."
)
