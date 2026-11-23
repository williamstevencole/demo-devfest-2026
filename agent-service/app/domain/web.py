"""Web search result model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WebResult:
    """One web result with enough provenance for citations."""

    title: str
    url: str
    snippet: str
    published_at: str | None
    source: str
