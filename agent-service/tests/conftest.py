import os
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("GOOGLE_API_KEY", "test-google-key")
os.environ.setdefault("CHAT_MODEL", "gemini-test")
os.environ.setdefault("EMBEDDING_MODEL", "test-embedding")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("LLM_TEMPERATURE", "0.2")
os.environ["AGENT_ENV_FILE"] = str(Path(__file__).with_name(".env.test-missing"))

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.domain.models import EtfHolding, Portfolio, Position, User
from app.main import create_app

PRICE_AS_OF = datetime(2026, 11, 17, tzinfo=UTC)


def _holding(
    ticker: str,
    weight: float,
    sector: str | None = None,
    name: str | None = None,
) -> EtfHolding:
    return EtfHolding(
        component_ticker=ticker,
        weight_pct=weight,
        component_sector=sector,
        component_name=name,
    )


def _position(
    ticker: str,
    instrument_type: str,
    quantity: float,
    price: float,
    holdings: tuple[EtfHolding, ...] = (),
    avg_cost: float | None = None,
    sector: str | None = None,
) -> Position:
    cost = price if avg_cost is None else avg_cost
    return Position(
        ticker=ticker,
        name=ticker,
        type=instrument_type,
        sector=sector,
        quantity=quantity,
        avg_cost_usd=cost,
        price_usd=price,
        market_value_usd=quantity * price,
        weight_pct=0,
        unrealized_pnl_usd=(price - cost) * quantity,
        price_as_of=PRICE_AS_OF,
        etf_holdings=list(holdings),
    )


def _portfolio(
    user_id: str, name: str, risk_profile: str, cash: float, positions: list[Position]
) -> Portfolio:
    invested = round(sum(position.market_value_usd for position in positions), 2)
    for position in positions:
        position.weight_pct = round(position.market_value_usd / invested * 100, 1)
    return Portfolio(
        user=User(
            id=user_id,
            name=name,
            email=f"{user_id}@example.com",
            risk_profile=risk_profile,
            country="Honduras",
            cash_usd=cash,
        ),
        positions=positions,
        cash_usd=cash,
        invested_usd=invested,
        total_usd=round(invested + cash, 2),
    )


@pytest.fixture
def maria() -> Portfolio:
    qqq = [
        _holding("NVDA", 9, "Technology", "NVIDIA Corporation"),
        _holding("AAPL", 8, "Technology", "Apple Inc."),
        _holding("MSFT", 7.5, "Technology", "Microsoft Corporation"),
        _holding("AMZN", 5.5, "Consumer Discretionary", "Amazon.com, Inc."),
        _holding("META", 4.5, "Communication Services", "Meta Platforms, Inc."),
    ]
    voo = [
        _holding("NVDA", 7, "Technology", "NVIDIA Corporation"),
        _holding("AAPL", 6.5, "Technology", "Apple Inc."),
        _holding("MSFT", 6, "Technology", "Microsoft Corporation"),
        _holding("AMZN", 3.5, "Consumer Discretionary", "Amazon.com, Inc."),
        _holding("GOOGL", 3, "Communication Services", "Alphabet Inc."),
    ]
    return _portfolio(
        "maria-lopez",
        "María López",
        "MODERATE",
        2500,
        [
            _position("NVDA", "STOCK", 20, 180, avg_cost=150, sector="Technology"),
            _position(
                "QQQ",
                "ETF",
                10,
                520,
                tuple(qqq),
                avg_cost=480,
                sector="Technology",
            ),
            _position(
                "VOO",
                "ETF",
                15,
                550,
                tuple(voo),
                avg_cost=500,
                sector="Broad Market",
            ),
            _position("AAPL", "STOCK", 5, 230, avg_cost=200, sector="Technology"),
        ],
    )


class FakeNestClient:
    def __init__(self, healthy: bool) -> None:
        self.healthy = healthy

    async def health(self) -> bool:
        return self.healthy

    async def aclose(self) -> None:
        return None


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_nest_down() -> FakeNestClient:
    return FakeNestClient(healthy=False)


@pytest.fixture
def client(fake_nest_down: FakeNestClient) -> TestClient:
    app = create_app(lambda settings: SimpleNamespace(settings=settings, nest=fake_nest_down))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_nest_up() -> TestClient:
    app = create_app(
        lambda settings: SimpleNamespace(settings=settings, nest=FakeNestClient(healthy=True))
    )
    with TestClient(app) as test_client:
        yield test_client
