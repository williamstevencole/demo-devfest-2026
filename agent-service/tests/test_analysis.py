import pytest

from app.domain.analysis import (
    SaleScenario,
    analyze_portfolio,
    simulate_sale,
)
from app.domain.models import Portfolio
from app.errors import UnknownTickerError


def test_maria_nvda(maria: Portfolio) -> None:
    result = analyze_portfolio(maria, "NVDA")

    focus = result.focus_exposure
    assert focus is not None
    assert focus.direct_usd == 3600
    assert focus.indirect_usd == 1045.5
    assert focus.total_usd == 4645.5
    assert focus.weight_pct == 25.5
    assert result.cost_usd == 16300
    assert result.unrealized_pnl_usd == 1900


def test_maria_vende_qqq(maria: Portfolio) -> None:
    result = analyze_portfolio(
        maria,
        ticker="NVDA",
        simulate_sell=SaleScenario(ticker="QQQ"),
    )

    focus = result.focus_exposure
    assert focus is not None
    assert result.invested_usd == 13000
    assert result.total_value_usd == 20700
    assert result.cash_usd == 7700
    assert focus.direct_usd == 3600
    assert focus.indirect_usd == 577.5
    assert focus.total_usd == 4177.5
    assert focus.weight_pct == 32.1


def test_simulate_sale_equivale_al_parametro(maria: Portfolio) -> None:
    after = simulate_sale(maria, "QQQ")
    direct = analyze_portfolio(after, "NVDA")
    simulated = analyze_portfolio(maria, "NVDA", SaleScenario("QQQ"))

    assert simulated.focus_exposure == direct.focus_exposure


def test_venta_parcial_reduce_posicion_y_suma_efectivo(maria: Portfolio) -> None:
    after = simulate_sale(maria, "QQQ", quantity=4)

    qqq = next(position for position in after.positions if position.ticker == "QQQ")
    assert qqq.quantity == 6
    assert qqq.market_value_usd == 3120
    assert after.cash_usd == 4580
    assert after.invested_usd == 16120
    assert after.total_usd == 20700


def test_exposicion_incluye_componentes_de_etf(maria: Portfolio) -> None:
    result = analyze_portfolio(maria, "MSFT")

    focus = result.focus_exposure
    assert focus is not None
    assert focus.direct_usd == 0
    assert focus.indirect_usd == 885
    assert result.top_exposure is not None
    assert result.top_exposure.ticker == "VOO"


def test_sectores_incluyen_look_through(maria: Portfolio) -> None:
    sectors = {sector.sector: sector for sector in analyze_portfolio(maria).sectors}

    assert sectors["Technology"].total_usd == 10415
    assert sectors["Technology"].weight_pct == 57.2
    assert sectors["Financials"].total_usd == 1067.65
    assert sectors["Health Care"].total_usd == 1126.25
    assert "Sin detalle" not in sectors
    assert sum(sector.total_usd for sector in sectors.values()) == 18200


def test_venta_de_ticker_inexistente_falla(maria: Portfolio) -> None:
    with pytest.raises(UnknownTickerError):
        simulate_sale(maria, "TSLA")


def test_venta_con_cantidad_no_positiva_falla(maria: Portfolio) -> None:
    with pytest.raises(ValueError):
        simulate_sale(maria, "QQQ", quantity=0)


def test_venta_parcial_recalcula_pnl(maria: Portfolio) -> None:
    qqq = next(position for position in maria.positions if position.ticker == "QQQ")
    qqq.avg_cost_usd = 480
    qqq.unrealized_pnl_usd = 400

    after = simulate_sale(maria, "QQQ", quantity=4)

    updated = next(position for position in after.positions if position.ticker == "QQQ")
    assert updated.unrealized_pnl_usd == 240
