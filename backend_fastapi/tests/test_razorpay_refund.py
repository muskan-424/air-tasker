from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.razorpay_service import refund_payment


def test_refund_payment_posts_to_razorpay():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"id":"rfnd_1"}'
    mock_response.json.return_value = {"id": "rfnd_1", "amount": 10000, "status": "processed"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.services.razorpay_service.httpx.AsyncClient", return_value=mock_client):
        out = asyncio.run(
            refund_payment(
                key_id="rzp_test",
                key_secret="secret",
                payment_id="pay_abc",
                amount_paise=None,
            )
        )

    assert out["id"] == "rfnd_1"
    mock_client.post.assert_called_once()
    call_kw = mock_client.post.call_args
    assert "pay_abc/refund" in call_kw[0][0]


def test_refund_payment_raises_on_error_status():
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "bad"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "err", request=MagicMock(), response=mock_response
    )

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.services.razorpay_service.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(
                refund_payment(
                    key_id="rzp_test",
                    key_secret="secret",
                    payment_id="pay_abc",
                    amount_paise=int((Decimal("100.50") * Decimal(100)).quantize(Decimal("1"))),
                )
            )
