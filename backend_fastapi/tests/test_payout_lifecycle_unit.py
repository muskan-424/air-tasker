"""Unit tests for payout lifecycle helpers (no DB)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from app.services.payout_lifecycle_service import sync_payout_escrow_from_webhook


def test_sync_payout_returns_none_for_non_payout_event():
    async def run() -> None:
        db = MagicMock()
        r = await sync_payout_escrow_from_webhook(
            db,
            event_type="payment.captured",
            payload={},
            razorpay_event_id=None,
        )
        assert r is None

    asyncio.run(run())


def test_sync_payout_returns_none_for_empty_event():
    async def run() -> None:
        db = MagicMock()
        r = await sync_payout_escrow_from_webhook(db, event_type=None, payload={}, razorpay_event_id=None)
        assert r is None

    asyncio.run(run())
