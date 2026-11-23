"""Prompt for the honest naive RAG mode."""

from collections.abc import Sequence
from typing import Any

SYSTEM = """Responde en español usando solo el contexto recuperado. Si el
contexto no alcanza, dilo con claridad. Responde solo lo que se pregunta; no
agregues advertencias sobre temas que no aparecen en la pregunta."""


def _history_block(history: list[dict[str, str]] | None) -> str:
    lines: list[str] = []
    for message in (history or [])[-8:]:
        content = message.get("content", "").strip()
        if not content:
            continue
        role = "Usuario" if message.get("role") == "user" else "Asistente"
        lines.append(f"{role}: {content[:600]}")
    return "\n".join(lines)


def build_naive_prompt(
    query: str,
    documents: Sequence[Any],
    history: list[dict[str, str]] | None = None,
) -> str:
    """Build the one-shot naive RAG prompt."""

    context = "\n\n".join(
        f"[{document.source} > {document.section}]\n{document.text}" for document in documents
    )
    recent = _history_block(history)
    parts = [
        SYSTEM,
        f"Contexto:\n{context or '(sin contexto)'}",
    ]
    if recent:
        parts.extend(
            [
                f"Conversación reciente:\n{recent}",
                "Usa la conversación solo para entender a qué se refiere la " "pregunta actual.",
            ]
        )
    parts.extend(
        [
            f"Pregunta: {query}",
            "Cubre cada parte de la pregunta y menciona las condiciones y cifras "
            "relevantes del contexto, incluidas comisiones (aunque sean $0), "
            "spreads y condiciones cuando aparezcan.",
            "Si el contexto indica que la comisión de operar es $0, menciónalo "
            "explícitamente al hablar de costos.",
            "Responde citando [archivo.md > Sección] cuando uses el contexto.",
        ]
    )
    return "\n\n".join(parts)
