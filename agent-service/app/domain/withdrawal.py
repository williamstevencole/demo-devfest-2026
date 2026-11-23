"""Pure withdrawal models, constants and estimation."""

from dataclasses import dataclass

from app.domain.models import Portfolio
from app.errors import InsufficientFundsError

FX_SPREAD_PCT = 0.75
SETTLEMENT_NOTE = "T+1 para la venta; 2–3 días hábiles para el retiro"
TRADING_FEE_USD = 0.0


@dataclass(frozen=True)
class WithdrawalEstimate:
    """Cost breakdown for a hypothetical withdrawal."""

    amount_usd: float
    cash_used_usd: float
    sell_amount_usd: float
    trading_fee_usd: float
    fx_spread_usd: float
    total_fees_usd: float
    net_amount_usd: float
    settlement: str
    can_withdraw_today: bool


PERCENT = 100.0


def estimate_withdrawal(
    portfolio: Portfolio,
    amount_usd: float,
    convert_to_local: bool = True,
) -> WithdrawalEstimate:
    """Estimate cash, sales and fees for withdrawing an amount.

    ``convert_to_local`` keeps the historical demo behaviour of converting the
    withdrawal to the local currency. Pass ``False`` for a USD withdrawal, where
    there is no FX spread.
    """

    amount = round(amount_usd, 2)
    if amount > round(portfolio.total_usd, 2):
        raise InsufficientFundsError("El monto solicitado supera el valor total del portafolio")
    cash_used = round(min(portfolio.cash_usd, amount), 2)
    sell_amount = round(max(0.0, amount - portfolio.cash_usd), 2)
    fx_spread = round(amount * FX_SPREAD_PCT / PERCENT, 2) if convert_to_local else 0.0
    total_fees = round(TRADING_FEE_USD + fx_spread, 2)
    net_amount = round(amount - total_fees, 2)
    return WithdrawalEstimate(
        amount_usd=amount,
        cash_used_usd=cash_used,
        sell_amount_usd=sell_amount,
        trading_fee_usd=TRADING_FEE_USD,
        fx_spread_usd=fx_spread,
        total_fees_usd=total_fees,
        net_amount_usd=net_amount,
        settlement=SETTLEMENT_NOTE,
        can_withdraw_today=sell_amount == 0,
    )
