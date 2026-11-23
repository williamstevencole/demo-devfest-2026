from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.domain.models import Portfolio
from app.main import create_app


class FakeNest:
    def __init__(self, portfolio: Portfolio | None) -> None:
        self._portfolio = portfolio

    async def get_portfolio(self, user_id: str) -> Portfolio | None:
        if user_id == "maria-lopez":
            return self._portfolio
        return None

    async def aclose(self) -> None:
        return None


def _client(portfolio: Portfolio | None) -> TestClient:
    app = create_app(
        lambda settings: SimpleNamespace(
            settings=settings,
            nest=FakeNest(portfolio),
        )
    )
    return TestClient(app)


def test_portfolio_devuelve_distribucion_sin_limite(maria: Portfolio) -> None:
    with _client(maria) as client:
        response = client.get("/api/portfolio/maria-lopez")

    body = response.json()
    assert response.status_code == 200
    assert body["invested_usd"] == 18200
    assert body["cash_usd"] == 2500
    assert body["total_value_usd"] == 20700
    assert body["cost_usd"] == 16300
    assert body["unrealized_pnl_usd"] == 1900
    assert len(body["positions"]) == 4
    assert body["positions"][0]["ticker"] == "NVDA"
    assert body["positions"][0]["etfHoldings"] == []
    qqq = next(position for position in body["positions"] if position["ticker"] == "QQQ")
    assert qqq["etfHoldings"][0]["componentTicker"] == "NVDA"
    assert qqq["etfHoldings"][0]["weightPct"] == 9
    assert "limit_pct" not in body
    assert all("over_limit" not in exposure for exposure in body["exposures"])


def test_portfolio_inexistente_devuelve_404() -> None:
    with _client(None) as client:
        response = client.get("/api/portfolio/nadie")

    assert response.status_code == 404
