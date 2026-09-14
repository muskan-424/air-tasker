"""Service fees: what the poster pays, what the platform keeps, what the tasker receives."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.core.config import settings

_CENT = Decimal("0.01")


def _money(value: Decimal | float | str) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _percent_fee(price: Decimal, percent: float) -> Decimal:
    if percent <= 0 or price <= 0:
        return Decimal("0.00")
    fee = _money(price * Decimal(str(percent)) / Decimal(100))
    return max(fee, _money(settings.service_fee_min_inr))


@dataclass(frozen=True)
class FeeBreakdown:
    task_price: Decimal
    poster_fee: Decimal
    poster_total: Decimal
    tasker_fee: Decimal
    tasker_payout: Decimal

    def as_dict(self) -> dict[str, str]:
        return {
            "task_price": str(self.task_price),
            "poster_fee": str(self.poster_fee),
            "poster_total": str(self.poster_total),
            "tasker_fee": str(self.tasker_fee),
            "tasker_payout": str(self.tasker_payout),
        }


def compute_fees(task_price: Decimal | float | str) -> FeeBreakdown:
    price = _money(task_price)
    poster_fee = _percent_fee(price, settings.poster_service_fee_percent)
    # The tasker fee can never exceed the price itself.
    tasker_fee = min(_percent_fee(price, settings.tasker_service_fee_percent), price)
    return FeeBreakdown(
        task_price=price,
        poster_fee=poster_fee,
        poster_total=price + poster_fee,
        tasker_fee=tasker_fee,
        tasker_payout=price - tasker_fee,
    )


def cancellation_fee(task_price: Decimal | float | str) -> Decimal:
    price = _money(task_price)
    if settings.cancellation_fee_percent <= 0 or price <= 0:
        return Decimal("0.00")
    return min(_money(price * Decimal(str(settings.cancellation_fee_percent)) / Decimal(100)), price)
