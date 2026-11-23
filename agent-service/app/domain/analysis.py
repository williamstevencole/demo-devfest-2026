"""Pure portfolio analysis models and calculations."""

from dataclasses import dataclass

from app.domain.models import Portfolio, Position
from app.errors import UnknownTickerError

UNKNOWN_SECTOR = "Sin detalle"
UNCLASSIFIED_SECTOR = "Sin sector"

# Full look-through sector allocation for the ETFs in the demo. The holdings
# table only stores the top positions, so relying on it leaves a large
# "Sin detalle" remainder. These profiles cover 100% of each fund and are used
# for sector exposure while the holdings list stays limited to the top names.
ETF_SECTOR_PROFILES: dict[str, dict[str, float]] = {
    "QQQ": {
        "Technology": 55.0,
        "Communication Services": 15.0,
        "Consumer Discretionary": 12.5,
        "Health Care": 5.0,
        "Industrials": 4.0,
        "Consumer Staples": 4.0,
        "Utilities": 1.5,
        "Materials": 1.5,
        "Financials": 0.7,
        "Energy": 0.5,
        "Real Estate": 0.3,
    },
    "VOO": {
        "Technology": 34.0,
        "Financials": 12.5,
        "Health Care": 10.5,
        "Consumer Discretionary": 10.0,
        "Communication Services": 9.5,
        "Industrials": 8.0,
        "Consumer Staples": 5.5,
        "Energy": 3.5,
        "Utilities": 2.2,
        "Real Estate": 2.0,
        "Materials": 2.3,
    },
}


@dataclass(frozen=True)
class SaleScenario:
    """A hypothetical full or partial sale."""

    ticker: str
    quantity: float | None = None


@dataclass(frozen=True)
class Exposure:
    """Direct and ETF look-through exposure to one ticker."""

    ticker: str
    direct_usd: float
    indirect_usd: float
    total_usd: float
    weight_pct: float


@dataclass(frozen=True)
class SectorExposure:
    """Look-through exposure grouped by sector."""

    sector: str
    direct_usd: float
    indirect_usd: float
    total_usd: float
    weight_pct: float


@dataclass
class PortfolioAnalysis:
    """Deterministic portfolio figures consumed by the response node."""

    invested_usd: float
    total_value_usd: float
    cash_usd: float
    cost_usd: float
    unrealized_pnl_usd: float
    positions: list[Position]
    exposures: list[Exposure]
    sectors: list[SectorExposure]
    top_exposure: Exposure | None
    focus_exposure: Exposure | None
    disclaimer_required: bool


PERCENT = 100.0


def _round_money(value: float) -> float:
    return round(value, 2)


def _round_pct(value: float) -> float:
    return round(value, 1)


def _reweight(positions: list[Position], invested: float) -> None:
    for position in positions:
        weight = position.market_value_usd / invested * PERCENT if invested else 0.0
        position.weight_pct = _round_pct(weight)


def simulate_sale(portfolio: Portfolio, ticker: str, quantity: float | None = None) -> Portfolio:
    """Return a copy of the portfolio after selling a full or partial position."""

    updated = portfolio.model_copy(deep=True)
    target = ticker.upper()
    position = next((item for item in updated.positions if item.ticker.upper() == target), None)
    if position is None:
        raise UnknownTickerError(f"No position for {target}")

    if quantity is not None and quantity <= 0:
        raise ValueError("Sale quantity must be positive")

    sell_quantity = position.quantity if quantity is None else min(quantity, position.quantity)
    proceeds = _round_money(sell_quantity * position.price_usd)
    remaining = position.quantity - sell_quantity
    if remaining <= 0:
        updated.positions = [item for item in updated.positions if item.ticker != position.ticker]
    else:
        position.quantity = remaining
        position.market_value_usd = _round_money(remaining * position.price_usd)
        position.unrealized_pnl_usd = _round_money(
            (position.price_usd - position.avg_cost_usd) * remaining
        )

    updated.cash_usd = _round_money(updated.cash_usd + proceeds)
    updated.invested_usd = _round_money(updated.invested_usd - proceeds)
    updated.total_usd = _round_money(updated.cash_usd + updated.invested_usd)
    updated.user.cash_usd = updated.cash_usd
    _reweight(updated.positions, updated.invested_usd)
    return updated


def _collect_exposures(portfolio: Portfolio) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for position in portfolio.positions:
        direct = totals.setdefault(position.ticker.upper(), {"direct": 0.0, "indirect": 0.0})
        direct["direct"] += position.market_value_usd
        for holding in position.etf_holdings:
            component = totals.setdefault(
                holding.component_ticker.upper(),
                {"direct": 0.0, "indirect": 0.0},
            )
            component["indirect"] += position.market_value_usd * holding.weight_pct / PERCENT
    return totals


def _build_exposure(ticker: str, amounts: dict[str, float], invested: float) -> Exposure:
    direct_usd = _round_money(amounts["direct"])
    indirect_usd = _round_money(amounts["indirect"])
    total_usd = _round_money(direct_usd + indirect_usd)
    weight = total_usd / invested * PERCENT if invested else 0.0
    weight_pct = _round_pct(weight)
    return Exposure(
        ticker=ticker,
        direct_usd=direct_usd,
        indirect_usd=indirect_usd,
        total_usd=total_usd,
        weight_pct=weight_pct,
    )


def _collect_sectors(portfolio: Portfolio) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for position in portfolio.positions:
        if not position.etf_holdings:
            sector = position.sector or UNCLASSIFIED_SECTOR
            bucket = totals.setdefault(sector, {"direct": 0.0, "indirect": 0.0})
            bucket["direct"] += position.market_value_usd
            continue
        profile = ETF_SECTOR_PROFILES.get(position.ticker.upper())
        if profile:
            for sector, weight in profile.items():
                bucket = totals.setdefault(sector, {"direct": 0.0, "indirect": 0.0})
                bucket["indirect"] += position.market_value_usd * weight / PERCENT
            continue
        known = 0.0
        for holding in position.etf_holdings:
            sector = holding.component_sector or UNKNOWN_SECTOR
            bucket = totals.setdefault(sector, {"direct": 0.0, "indirect": 0.0})
            bucket["indirect"] += position.market_value_usd * holding.weight_pct / PERCENT
            known += holding.weight_pct
        remainder = max(0.0, PERCENT - known)
        if remainder:
            bucket = totals.setdefault(UNKNOWN_SECTOR, {"direct": 0.0, "indirect": 0.0})
            bucket["indirect"] += position.market_value_usd * remainder / PERCENT
    return totals


def _build_sector(sector: str, amounts: dict[str, float], invested: float) -> SectorExposure:
    direct_usd = _round_money(amounts["direct"])
    indirect_usd = _round_money(amounts["indirect"])
    total_usd = _round_money(direct_usd + indirect_usd)
    weight = total_usd / invested * PERCENT if invested else 0.0
    return SectorExposure(
        sector=sector,
        direct_usd=direct_usd,
        indirect_usd=indirect_usd,
        total_usd=total_usd,
        weight_pct=_round_pct(weight),
    )


def analyze_portfolio(
    portfolio: Portfolio,
    ticker: str | None = None,
    simulate_sell: SaleScenario | None = None,
) -> PortfolioAnalysis:
    """Calculate values, weights and look-through exposure for a portfolio."""

    current = (
        simulate_sale(portfolio, simulate_sell.ticker, simulate_sell.quantity)
        if simulate_sell
        else portfolio
    )
    amounts = _collect_exposures(current)
    exposures = [
        _build_exposure(name, values, current.invested_usd) for name, values in amounts.items()
    ]
    exposures.sort(key=lambda item: (-item.total_usd, item.ticker))
    sectors = [
        _build_sector(name, values, current.invested_usd)
        for name, values in _collect_sectors(current).items()
    ]
    sectors.sort(key=lambda item: (-item.total_usd, item.sector))
    focus = None
    if ticker:
        focus = next((item for item in exposures if item.ticker == ticker.upper()), None)
    top = exposures[0] if exposures else None
    cost = _round_money(
        sum(position.quantity * position.avg_cost_usd for position in current.positions)
    )
    unrealized = _round_money(sum(position.unrealized_pnl_usd for position in current.positions))
    return PortfolioAnalysis(
        invested_usd=current.invested_usd,
        total_value_usd=current.total_usd,
        cash_usd=current.cash_usd,
        cost_usd=cost,
        unrealized_pnl_usd=unrealized,
        positions=current.positions,
        exposures=exposures,
        sectors=sectors,
        top_exposure=top,
        focus_exposure=focus,
        disclaimer_required=False,
    )


def sale_impact(
    baseline: PortfolioAnalysis,
    analysis: PortfolioAnalysis,
    scenario: SaleScenario,
) -> dict | None:
    """Describe the deterministic change caused by a hypothetical sale."""

    previous = {exposure.ticker: exposure for exposure in baseline.exposures}
    changes = []
    for exposure in analysis.exposures:
        before = previous.get(exposure.ticker)
        if before is None:
            continue
        total_delta = round(exposure.total_usd - before.total_usd, 2)
        indirect_delta = round(exposure.indirect_usd - before.indirect_usd, 2)
        if total_delta == 0 and indirect_delta == 0:
            continue
        changes.append(
            {
                "ticker": exposure.ticker,
                "before_total_usd": before.total_usd,
                "after_total_usd": exposure.total_usd,
                "total_change_usd": total_delta,
                "indirect_change_usd": indirect_delta,
                "after_weight_pct": exposure.weight_pct,
            }
        )
    if not changes:
        return None
    return {
        "ticker": scenario.ticker,
        "quantity": scenario.quantity,
        "before_invested_usd": baseline.invested_usd,
        "after_invested_usd": analysis.invested_usd,
        "before_cash_usd": baseline.cash_usd,
        "after_cash_usd": analysis.cash_usd,
        "before_total_usd": baseline.total_value_usd,
        "after_total_usd": analysis.total_value_usd,
        "exposure_changes": changes,
    }
