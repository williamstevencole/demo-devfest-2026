import httpx
import pytest

from app.errors import NestUnavailableError
from app.integrations.nest import HEALTH_TIMEOUT_SECONDS, NestClient

PORTFOLIO_PAYLOAD = {
    "user": {
        "id": "maria-lopez",
        "name": "María López",
        "email": "maria@example.com",
        "riskProfile": "MODERATE",
        "country": "Honduras",
        "cashUsd": 2500,
    },
    "positions": [
        {
            "ticker": "NVDA",
            "name": "NVIDIA",
            "type": "STOCK",
            "sector": "Technology",
            "quantity": 20,
            "avgCostUsd": 150,
            "priceUsd": 180,
            "marketValueUsd": 3600,
            "weightPct": 19.8,
            "unrealizedPnlUsd": 600,
            "priceAsOf": "2026-11-17T00:00:00.000Z",
            "etfHoldings": [],
        },
        {
            "ticker": "QQQ",
            "name": "Invesco QQQ",
            "type": "ETF",
            "sector": None,
            "quantity": 10,
            "avgCostUsd": 480,
            "priceUsd": 520,
            "marketValueUsd": 5200,
            "weightPct": 28.6,
            "unrealizedPnlUsd": 400,
            "priceAsOf": "2026-11-17T00:00:00.000Z",
            "etfHoldings": [{"componentTicker": "NVDA", "weightPct": 9}],
        },
    ],
    "cashUsd": 2500,
    "investedUsd": 18200,
    "totalUsd": 20700,
}


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/users/maria-lopez/portfolio":
        return httpx.Response(200, json=PORTFOLIO_PAYLOAD)
    if request.url.path in {"/api/users/missing", "/api/users/missing/portfolio"}:
        return httpx.Response(404, json={"message": "not found"})
    if request.url.path == "/api/health":
        return httpx.Response(200, json={"status": "ok"})
    return httpx.Response(500, json={"message": "boom"})


def _client(handler=_handler) -> NestClient:
    return NestClient("http://nest", 1.0, transport=httpx.MockTransport(handler))


async def test_portfolio_parsea_alias_camel_case() -> None:
    portfolio = await _client().get_portfolio("maria-lopez")

    assert portfolio is not None
    assert portfolio.cash_usd == 2500
    assert portfolio.invested_usd == 18200
    assert portfolio.total_usd == 20700
    assert portfolio.user.risk_profile == "MODERATE"
    assert portfolio.positions[0].market_value_usd == 3600
    assert portfolio.positions[0].avg_cost_usd == 150
    assert portfolio.positions[1].etf_holdings[0].component_ticker == "NVDA"
    assert portfolio.positions[1].etf_holdings[0].weight_pct == 9


async def test_404_devuelve_none() -> None:
    assert await _client().get_portfolio("missing") is None


async def test_timeout_es_error_tipado() -> None:
    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(NestUnavailableError):
        await _client(failing_handler).get_portfolio("x")


async def test_5xx_es_error_tipado() -> None:
    with pytest.raises(NestUnavailableError):
        await _client().get_portfolio("x")


async def test_health_devuelve_bool() -> None:
    assert await _client().health() is True


async def test_health_falso_si_nest_responde_error() -> None:
    def broken_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    assert await _client(broken_handler).health() is False


async def test_health_usa_timeout_corto_y_los_datos_el_configurado() -> None:
    seen: dict[str, dict | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen[request.url.path] = request.extensions.get("timeout")
        if request.url.path == "/api/health":
            return httpx.Response(200)
        return httpx.Response(404)

    client = NestClient("http://nest", timeout=7.0, transport=httpx.MockTransport(handler))

    await client.health()
    await client.get_portfolio("missing")

    assert seen["/api/health"]["read"] == HEALTH_TIMEOUT_SECONDS
    assert seen["/api/users/missing/portfolio"]["read"] == 7.0


async def test_404_de_portfolio_devuelve_none() -> None:
    def missing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    client = _client(missing_handler)

    assert await client.get_portfolio("missing") is None
