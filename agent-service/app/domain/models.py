"""Pydantic models for the Nest API payloads."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

RiskProfile = Literal["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]
InstrumentType = Literal["STOCK", "ETF"]


class NestModel(BaseModel):
    """Base model that accepts Nest's camelCase payloads."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class User(NestModel):
    """Read-only user profile."""

    id: str
    identity_number: str | None = None
    name: str
    email: str
    risk_profile: RiskProfile
    country: str
    cash_usd: float


class EtfHolding(NestModel):
    """One component of an ETF."""

    component_ticker: str
    weight_pct: float
    component_name: str | None = None
    component_sector: str | None = None


class Position(NestModel):
    """A valued position in a portfolio."""

    ticker: str
    name: str
    type: InstrumentType
    sector: str | None
    quantity: float
    avg_cost_usd: float
    price_usd: float
    market_value_usd: float
    weight_pct: float
    unrealized_pnl_usd: float
    price_as_of: datetime | None
    etf_holdings: list[EtfHolding]


class Portfolio(NestModel):
    """A user's portfolio with deterministic totals from Nest."""

    user: User
    positions: list[Position]
    cash_usd: float
    invested_usd: float
    total_usd: float
