import pytest

from app.domain.models import Portfolio
from app.domain.withdrawal import (
    FX_SPREAD_PCT,
    SETTLEMENT_NOTE,
    estimate_withdrawal,
)
from app.errors import InsufficientFundsError


def test_maria_retira_5000(maria: Portfolio) -> None:
    result = estimate_withdrawal(maria, 5000)

    assert result.amount_usd == 5000
    assert result.cash_used_usd == 2500
    assert result.sell_amount_usd == 2500
    assert result.trading_fee_usd == 0
    assert result.fx_spread_usd == 37.5
    assert result.total_fees_usd == 37.5
    assert result.net_amount_usd == 4962.5
    assert result.settlement == SETTLEMENT_NOTE
    assert result.can_withdraw_today is False


def test_retiro_cubierto_por_efectivo_sale_hoy(maria: Portfolio) -> None:
    result = estimate_withdrawal(maria, 1000)

    assert result.cash_used_usd == 1000
    assert result.sell_amount_usd == 0
    assert result.fx_spread_usd == 7.5
    assert result.net_amount_usd == 992.5
    assert result.can_withdraw_today is True


def test_constantes_del_contrato() -> None:
    assert FX_SPREAD_PCT == 0.75


def test_retiro_mayor_al_total_falla(maria: Portfolio) -> None:
    with pytest.raises(InsufficientFundsError):
        estimate_withdrawal(maria, 20700.01)


def test_retiro_igual_al_total_es_posible(maria: Portfolio) -> None:
    result = estimate_withdrawal(maria, 20700)

    assert result.sell_amount_usd == 18200
    assert result.net_amount_usd == 20544.75
    assert result.can_withdraw_today is False
