"""Deterministic data functions exposed to the autonomous agent as tools."""

import json
import unicodedata
from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from app.domain.analysis import (
    PortfolioAnalysis,
    SaleScenario,
    analyze_portfolio,
    sale_impact,
)
from app.domain.response import analysis_payload
from app.domain.withdrawal import FX_SPREAD_PCT, estimate_withdrawal
from app.errors import InsufficientFundsError, UnknownTickerError

DEFAULT_MOVES = (-20.0, -10.0, 10.0, 20.0)
PERCENT = 100.0
NON_NEWS_DOMAINS = (
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "facebook.com",
    "twitter.com",
    "x.com",
)


def _is_press(result: Any) -> bool:
    source = str(getattr(result, "source", "")).lower()
    return not any(domain in source for domain in NON_NEWS_DOMAINS)


def _error(message: str, **extra: Any) -> dict[str, Any]:
    return {"error": message, **extra}


def _no_user() -> dict[str, Any]:
    return _error(
        "No hay un usuario configurado en esta demo. Revisa DEMO_USER en la UI "
        "o envía un user_id válido."
    )


def _no_portfolio(user_id: str) -> dict[str, Any]:
    return _error(f"No encontramos un portafolio para el usuario {user_id}.")


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


SECTOR_ALIASES = {
    "tecnologia": "Technology",
    "technology": "Technology",
    "consumo discrecional": "Consumer Discretionary",
    "consumer discretionary": "Consumer Discretionary",
    "comunicaciones": "Communication Services",
    "communication services": "Communication Services",
    "renta fija": "Fixed Income",
    "fixed income": "Fixed Income",
    "consumo basico": "Consumer Staples",
    "consumer staples": "Consumer Staples",
    "sin detalle": "Sin detalle",
    "sin sector": "Sin sector",
}


def _resolve_ticker(portfolio: Any, target: str) -> str | None:
    """Map a company name (NVIDIA, Apple) to the ticker held in the portfolio."""

    normalized = _normalize(target)
    for position in portfolio.positions:
        if normalized == _normalize(position.ticker) or normalized in _normalize(position.name):
            return position.ticker
        for holding in position.etf_holdings:
            if normalized == _normalize(holding.component_ticker):
                return holding.component_ticker
            if holding.component_name and normalized in _normalize(holding.component_name):
                return holding.component_ticker
    return None


def _find_exposure(analysis: PortfolioAnalysis, target: str) -> dict[str, Any] | None:
    ticker = target.strip().upper()
    for exposure in analysis.exposures:
        if exposure.ticker.upper() == ticker:
            return {
                "kind": "ticker",
                "target": exposure.ticker,
                "direct_usd": exposure.direct_usd,
                "indirect_usd": exposure.indirect_usd,
                "total_usd": exposure.total_usd,
                "weight_invested_pct": exposure.weight_pct,
                "weight_total_pct": (
                    round(exposure.total_usd / analysis.total_value_usd * PERCENT, 2)
                    if analysis.total_value_usd
                    else 0.0
                ),
            }

    normalized = SECTOR_ALIASES.get(_normalize(target), target)
    for sector in analysis.sectors:
        if _normalize(sector.sector) == _normalize(normalized):
            return {
                "kind": "sector",
                "target": sector.sector,
                "direct_usd": sector.direct_usd,
                "indirect_usd": sector.indirect_usd,
                "total_usd": sector.total_usd,
                "weight_invested_pct": sector.weight_pct,
                "weight_total_pct": (
                    round(sector.total_usd / analysis.total_value_usd * PERCENT, 2)
                    if analysis.total_value_usd
                    else 0.0
                ),
            }
    return None


def _available_targets(analysis: PortfolioAnalysis) -> dict[str, list[str]]:
    return {
        "available_tickers": [exposure.ticker for exposure in analysis.exposures],
        "available_sectors": [sector.sector for sector in analysis.sectors],
    }


async def analyze_portfolio_data(nest: Any, user_id: str) -> dict[str, Any]:
    """Return the full deterministic portfolio analysis."""

    if not user_id.strip():
        return _no_user()
    portfolio = await nest.get_portfolio(user_id)
    if portfolio is None:
        return _no_portfolio(user_id)
    analysis = analyze_portfolio(portfolio)
    return {
        "kind": "analysis",
        "user": portfolio.user.name,
        "data": analysis_payload(analysis),
    }


async def withdrawal_data(
    nest: Any,
    user_id: str,
    amount_usd: float,
    convert_to_local: bool = False,
) -> dict[str, Any]:
    """Estimate a withdrawal, including both USD and converted scenarios."""

    if not user_id.strip():
        return _no_user()
    portfolio = await nest.get_portfolio(user_id)
    if portfolio is None:
        return _no_portfolio(user_id)
    try:
        estimate = estimate_withdrawal(portfolio, amount_usd, convert_to_local=convert_to_local)
    except InsufficientFundsError as exc:
        return _error(str(exc), available_cash_usd=portfolio.cash_usd)
    conversion_spread = round(amount_usd * FX_SPREAD_PCT / PERCENT, 2)
    return {
        "kind": "withdrawal",
        "data": asdict(estimate),
        "conversion_spread_usd": conversion_spread,
        "net_if_converted_usd": round(amount_usd - conversion_spread, 2),
        "currency": "local" if convert_to_local else "USD",
        "citation": {
            "source": "comisiones_y_tarifas.md",
            "section": "Retiro y plazos",
        },
    }


async def sale_data(
    nest: Any,
    user_id: str,
    ticker: str,
    quantity: float | None = None,
) -> dict[str, Any]:
    """Simulate a sale and return the post-sale analysis and exposure changes."""

    if not user_id.strip():
        return _no_user()
    portfolio = await nest.get_portfolio(user_id)
    if portfolio is None:
        return _no_portfolio(user_id)
    scenario = SaleScenario(ticker=ticker.strip().upper(), quantity=quantity)
    try:
        baseline = analyze_portfolio(portfolio)
        analysis = analyze_portfolio(portfolio, simulate_sell=scenario)
    except UnknownTickerError:
        return _error(
            f"No tienes una posición en {scenario.ticker}.",
            available_tickers=[position.ticker for position in portfolio.positions],
        )
    return {
        "kind": "sale",
        "data": analysis_payload(analysis),
        "impact": sale_impact(baseline, analysis, scenario),
    }


async def scenario_data(
    nest: Any,
    user_id: str,
    target: str,
    moves_pct: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Return direct/indirect exposure and portfolio impact for a ticker or sector."""

    if not user_id.strip():
        return _no_user()
    portfolio = await nest.get_portfolio(user_id)
    if portfolio is None:
        return _no_portfolio(user_id)
    analysis = analyze_portfolio(portfolio)
    exposure = _find_exposure(analysis, _resolve_ticker(portfolio, target) or target)
    if exposure is None:
        return _error(
            f"No encuentro {target!r} entre tus posiciones ni sectores. "
            "Para un evento macro, elige el sector o ticker afectado y vuelve a "
            "llamar scenario_impact.",
            **_available_targets(analysis),
            sector_exposure=[
                {
                    "sector": sector.sector,
                    "total_usd": sector.total_usd,
                    "weight_invested_pct": sector.weight_pct,
                }
                for sector in analysis.sectors
            ],
        )
    moves = list(moves_pct or DEFAULT_MOVES)
    scenarios = []
    for move in moves:
        impact = round(exposure["total_usd"] * float(move) / PERCENT, 2)
        scenarios.append(
            {
                "move_pct": float(move),
                "impact_usd": impact,
                "impact_total_pct": (
                    round(impact / analysis.total_value_usd * PERCENT, 2)
                    if analysis.total_value_usd
                    else 0.0
                ),
            }
        )
    return {
        "kind": "scenario",
        "target": exposure["target"],
        "exposure": exposure,
        "scenarios": scenarios,
        "invested_usd": analysis.invested_usd,
        "total_value_usd": analysis.total_value_usd,
        "note": (
            "Es sensibilidad, no una predicción: mide cuánto cambiaría el valor "
            "si ese activo o sector cae ese porcentaje."
        ),
    }


def knowledge_data(knowledge: Any, query: str, top_k: int = 4) -> dict[str, Any]:
    """Return local corpus chunks with their citations."""

    hits = knowledge.search(query, top_k)
    return {
        "kind": "documents",
        "query": query,
        "documents": [
            {
                "source": hit.source,
                "section": hit.section,
                "text": hit.text,
                "score": hit.score,
            }
            for hit in hits
        ],
    }


async def news_data(web: Any, query: str) -> dict[str, Any]:
    """Return recent news results for the agent's query, newest first."""

    results = await web.search(query)
    press = [result for result in results if _is_press(result)]
    results = press or results
    ordered = sorted(
        results,
        key=lambda result: (
            result.published_at is not None,
            result.published_at or "",
        ),
        reverse=True,
    )
    items = [
        {
            "title": result.title,
            "url": result.url,
            "source": result.source,
            "published_at": result.published_at,
            "snippet": result.snippet,
        }
        for result in ordered
    ]
    return {
        "kind": "news",
        "query": query,
        "results": items,
        "latest": items[0] if items else None,
        "timeline": [
            {
                "published_at": item["published_at"],
                "title": item["title"],
                "url": item["url"],
            }
            for item in items
        ],
        "note": (
            "Resultados ordenados de la nota más reciente a la más antigua. "
            "'latest' es el estado más reciente conocido. Si 'latest' contradice "
            "una nota anterior, gana 'latest': la anterior está desactualizada."
        ),
    }


def as_tool_content(payload: dict[str, Any]) -> str:
    """Serialize a tool payload for the chat model."""

    return json.dumps(payload, ensure_ascii=False, default=str)


def sources_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract UI sources from a tool payload."""

    citation = payload.get("citation")
    if isinstance(citation, dict) and citation.get("source"):
        return [
            {
                "kind": "document",
                "label": f"{citation['source']} > {citation.get('section', '')}",
                "detail": "Condiciones de retiro del corpus.",
                "url": None,
            }
        ]
    kind = payload.get("kind")
    if kind == "documents":
        return [
            {
                "kind": "document",
                "label": f"{document['source']} > {document['section']}",
                "detail": document["text"][:200],
                "url": None,
            }
            for document in payload.get("documents", [])
        ]
    if kind == "news":
        sources = []
        for result in payload.get("results", []):
            meta = " · ".join(
                part
                for part in (
                    result.get("source", ""),
                    result.get("published_at") or "sin fecha",
                )
                if part
            )
            snippet = str(result.get("snippet") or "").strip()
            sources.append(
                {
                    "kind": "web",
                    "label": result.get("title") or result.get("source") or "Noticia",
                    "detail": f"{meta} — {snippet[:180]}" if snippet else meta,
                    "url": result.get("url"),
                }
            )
        return sources
    return []
