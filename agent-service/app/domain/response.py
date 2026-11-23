"""Response models shared by the answer node and the API."""

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from pydantic import BaseModel

from app.domain.analysis import PortfolioAnalysis
from app.domain.citations import source_label
from app.domain.trace import TraceStep


class SourceRef(BaseModel):
    """A citable document or web source."""

    kind: Literal["document", "web"]
    label: str
    detail: str
    url: str | None = None


DETAIL_LIMIT = 200


def _document_source(document: Any) -> SourceRef:
    return SourceRef(
        kind="document",
        label=source_label(document.source, document.section),
        detail=document.text[:DETAIL_LIMIT],
    )


def _web_source(result: Any) -> SourceRef:
    return SourceRef(
        kind="web",
        label=result.title or result.source,
        detail=f"{result.source} · {result.published_at or 'sin fecha'}",
        url=result.url,
    )


def collect_sources(documents: Sequence[Any], web_results: Sequence[Any]) -> list[SourceRef]:
    """Build a deduplicated, ordered source list for the response contract."""

    sources: list[SourceRef] = []
    seen_documents: set[tuple[str, str]] = set()
    for document in documents:
        key = (document.source, document.section)
        if key in seen_documents:
            continue
        seen_documents.add(key)
        sources.append(_document_source(document))
    seen_urls: set[str] = set()
    for result in web_results:
        if result.url in seen_urls:
            continue
        seen_urls.add(result.url)
        sources.append(_web_source(result))
    return sources


def analysis_payload(analysis: PortfolioAnalysis | None) -> dict[str, Any] | None:
    """Serialize the deterministic analysis into JSON-native values."""

    if analysis is None:
        return None
    return {
        "invested_usd": analysis.invested_usd,
        "total_value_usd": analysis.total_value_usd,
        "cash_usd": analysis.cash_usd,
        "cost_usd": analysis.cost_usd,
        "unrealized_pnl_usd": analysis.unrealized_pnl_usd,
        "positions": [
            position.model_dump(mode="json", by_alias=True) for position in analysis.positions
        ],
        "exposures": [asdict(exposure) for exposure in analysis.exposures],
        "sectors": [asdict(sector) for sector in analysis.sectors],
        "top_exposure": (
            asdict(analysis.top_exposure) if analysis.top_exposure is not None else None
        ),
        "focus_exposure": (
            asdict(analysis.focus_exposure) if analysis.focus_exposure is not None else None
        ),
        "disclaimer_required": analysis.disclaimer_required,
    }


@dataclass
class ChatResult:
    """Answer, trace and sources produced by one chat mode."""

    answer: str
    trace: list[TraceStep] = field(default_factory=list)
    sources: list[SourceRef] = field(default_factory=list)
    documents: list[Any] = field(default_factory=list)
    llm_error: bool = False
