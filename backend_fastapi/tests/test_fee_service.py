from decimal import Decimal

from app.core.config import settings
from app.services.fee_service import cancellation_fee, compute_fees


def test_compute_fees_default_percentages(monkeypatch):
    monkeypatch.setattr(settings, "poster_service_fee_percent", 5.0)
    monkeypatch.setattr(settings, "tasker_service_fee_percent", 10.0)
    monkeypatch.setattr(settings, "service_fee_min_inr", 10.0)

    fees = compute_fees(Decimal("1500"))

    assert fees.task_price == Decimal("1500.00")
    assert fees.poster_fee == Decimal("75.00")
    assert fees.poster_total == Decimal("1575.00")
    assert fees.tasker_fee == Decimal("150.00")
    assert fees.tasker_payout == Decimal("1350.00")


def test_compute_fees_applies_minimum_and_rounds(monkeypatch):
    monkeypatch.setattr(settings, "poster_service_fee_percent", 5.0)
    monkeypatch.setattr(settings, "tasker_service_fee_percent", 10.0)
    monkeypatch.setattr(settings, "service_fee_min_inr", 10.0)

    small = compute_fees("100")
    assert small.poster_fee == Decimal("10.00")  # 5.00 raised to the minimum
    assert small.tasker_fee == Decimal("10.00")

    odd = compute_fees("333.33")
    assert odd.poster_fee == Decimal("16.67")
    assert odd.tasker_payout == Decimal("300.00")


def test_zero_percent_disables_fees(monkeypatch):
    monkeypatch.setattr(settings, "poster_service_fee_percent", 0.0)
    monkeypatch.setattr(settings, "tasker_service_fee_percent", 0.0)

    fees = compute_fees("800")
    assert fees.poster_total == Decimal("800.00")
    assert fees.tasker_payout == Decimal("800.00")


def test_cancellation_fee(monkeypatch):
    monkeypatch.setattr(settings, "cancellation_fee_percent", 10.0)
    assert cancellation_fee("1500") == Decimal("150.00")
    monkeypatch.setattr(settings, "cancellation_fee_percent", 0.0)
    assert cancellation_fee("1500") == Decimal("0.00")
