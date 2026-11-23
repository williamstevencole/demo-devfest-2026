"""Deterministic guardrails for the agent's final answer."""

import json
import re
from collections.abc import Iterable
from typing import Any

URL_PATTERN = re.compile(r"https?://[^\s)>\]]+")


def allowed_urls_from_messages(messages: Iterable[Any]) -> set[str]:
    """Collect every URL that a tool actually returned."""

    allowed: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "url" and isinstance(item, str):
                    allowed.add(item.rstrip(".,)"))
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for message in messages:
        content = getattr(message, "content", None)
        if not isinstance(content, str):
            continue
        try:
            walk(json.loads(content))
        except ValueError:
            continue
    return allowed


def strip_unknown_urls(answer: str, allowed: set[str]) -> str:
    """Remove URLs the agent did not get from a tool.

    The model sometimes reconstructs a plausible-looking news URL. A wrong URL
    destroys trust in a finance demo, so only links that came from the tools
    survive.
    """

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        url = raw.rstrip(".,)")
        if url in allowed:
            return raw
        return ""

    cleaned = URL_PATTERN.sub(replace, answer)
    cleaned = re.sub(r"[,;:]\s*\)", ")", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


SECTION_PATTERN = re.compile(r"([\w.-]+\.md)(?:\s*[,;(]\s*secci[oó]n\s+([^).;\n]+))?")
MALFORMED_PERCENT = re.compile(r"\b(\d+)\.(\d+)\.(\d+)%")


def fix_malformed_percentages(answer: str) -> str:
    """Collapse percentages the model renders with a duplicated decimal point.

    A generated "26.9.5%" is a typo for "26.95%". Correcting it is safer than
    leaving a number that looks like a different figure.
    """

    return MALFORMED_PERCENT.sub(
        lambda match: f"{match.group(1)}.{match.group(2)}{match.group(3)}%",
        answer,
    )


TOOL_NAMES = (
    "search_knowledge",
    "search_news",
    "analyze_portfolio",
    "estimate_withdrawal",
    "simulate_sale",
    "scenario_impact",
)
TOOL_CITATION = re.compile(r"\s*\([^()]*\b(?:" + "|".join(TOOL_NAMES) + r")\b[^()]*\)")


def strip_tool_citations(answer: str) -> str:
    """Remove citations that name a tool instead of a real source.

    The model sometimes writes "(analyze_portfolio, 2026-11-23)" as if a tool
    were a published source. That is a fabricated citation, not a typo.
    """

    cleaned = TOOL_CITATION.sub("", answer)
    cleaned = re.sub(r"[ \t]+([.,;:])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _normalize(value: str) -> str:
    import unicodedata

    decomposed = unicodedata.normalize("NFKD", value.strip().casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def allowed_sections_from_messages(messages: Iterable[Any]) -> dict[str, set[str]]:
    """Collect the exact document sections that the knowledge tool returned."""

    allowed: dict[str, set[str]] = {}
    for message in messages:
        content = getattr(message, "content", None)
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except ValueError:
            continue
        if not isinstance(payload, dict):
            continue
        citation = payload.get("citation")
        if isinstance(citation, dict) and citation.get("source") and citation.get("section"):
            allowed.setdefault(citation["source"], set()).add(citation["section"])
        if payload.get("kind") != "documents":
            continue
        for document in payload.get("documents", []):
            source = document.get("source")
            section = document.get("section")
            if source and section:
                allowed.setdefault(source, set()).add(section)
    return allowed


def strip_unknown_sections(answer: str, allowed: dict[str, set[str]]) -> str:
    """Remove section names the model paraphrased or invented."""

    def replace(match: re.Match[str]) -> str:
        source = match.group(1)
        section = match.group(2)
        if source not in allowed:
            return ""
        if section and _normalize(section) not in {
            _normalize(candidate) for candidate in allowed[source]
        }:
            return source
        return match.group(0)

    cleaned = SECTION_PATTERN.sub(replace, answer)
    cleaned = re.sub(r"\b(según|en|de|ver)\s+\.", ".", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"`\s*([.,;])", r"\1", cleaned)
    cleaned = cleaned.replace("`", "")
    cleaned = re.sub(r"\*([\w.-]+\.md)", r"\1", cleaned)
    cleaned = re.sub(r"([\w.-]+\.md)\*", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()
