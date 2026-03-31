from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def verify_webhook_signature(body: bytes, signature: str | None, webhook_secret: str) -> bool:
    if not signature or not webhook_secret:
        return False
    expected = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def create_order(
    *,
    key_id: str,
    key_secret: str,
    amount_inr: Decimal,
    receipt: str,
    notes: dict[str, str],
) -> dict[str, Any]:
    amount_paise = int((amount_inr * Decimal(100)).quantize(Decimal("1")))
    auth = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
    payload = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt[:40],
        "notes": notes,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.razorpay.com/v1/orders",
            json=payload,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        )
        if r.status_code >= 400:
            logger.warning("Razorpay order create failed status=%s body=%s", r.status_code, r.text[:500])
        r.raise_for_status()
        return r.json()


async def refund_payment(
    *,
    key_id: str,
    key_secret: str,
    payment_id: str,
    amount_paise: int | None = None,
) -> dict[str, Any]:
    """POST /v1/payments/{id}/refund. Omit amount for full refund (in paise when partial)."""
    auth = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
    payload: dict[str, Any] = {}
    if amount_paise is not None:
        payload["amount"] = amount_paise
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"https://api.razorpay.com/v1/payments/{payment_id}/refund",
            json=payload,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        )
        if r.status_code >= 400:
            logger.warning(
                "Razorpay refund failed payment_id=%s status=%s body=%s",
                payment_id,
                r.status_code,
                r.text[:500],
            )
        r.raise_for_status()
        return r.json()


def _basic_auth_header(key_id: str, key_secret: str) -> str:
    return base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()


async def create_contact(
    *,
    key_id: str,
    key_secret: str,
    name: str,
    email: str,
    phone_digits: str,
    reference_id: str,
    contact_type: str = "vendor",
) -> dict[str, Any]:
    """POST /v1/contacts — RazorpayX Payouts."""
    auth = _basic_auth_header(key_id, key_secret)
    digits = "".join(c for c in phone_digits if c.isdigit())
    contact_phone = digits[-10:] if len(digits) >= 10 else "9999999999"
    payload = {
        "name": name[:50],
        "email": email,
        "contact": contact_phone,
        "type": contact_type,
        "reference_id": reference_id[:40],
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.razorpay.com/v1/contacts",
            json=payload,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        )
        if r.status_code >= 400:
            logger.warning("Razorpay contact create failed status=%s body=%s", r.status_code, r.text[:500])
        r.raise_for_status()
        return r.json()


async def create_fund_account_bank(
    *,
    key_id: str,
    key_secret: str,
    contact_id: str,
    beneficiary_name: str,
    ifsc: str,
    account_number: str,
) -> dict[str, Any]:
    """POST /v1/fund_accounts — bank_account type (India)."""
    auth = _basic_auth_header(key_id, key_secret)
    payload = {
        "contact_id": contact_id,
        "account_type": "bank_account",
        "bank_account": {
            "name": beneficiary_name[:50],
            "ifsc": ifsc.upper()[:11],
            "account_number": account_number,
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.razorpay.com/v1/fund_accounts",
            json=payload,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        )
        if r.status_code >= 400:
            logger.warning("Razorpay fund_account create failed status=%s body=%s", r.status_code, r.text[:500])
        r.raise_for_status()
        return r.json()


async def create_payout(
    *,
    key_id: str,
    key_secret: str,
    razorpayx_account_number: str,
    fund_account_id: str,
    amount_paise: int,
    currency: str,
    reference_id: str,
    idempotency_key: str,
    narration: str = "Task escrow payout",
) -> dict[str, Any]:
    """POST /v1/payouts — requires RazorpayX; uses `X-Payout-Idempotency` header."""
    auth = _basic_auth_header(key_id, key_secret)
    payload = {
        "account_number": razorpayx_account_number,
        "fund_account_id": fund_account_id,
        "amount": amount_paise,
        "currency": currency,
        "mode": "IMPS",
        "purpose": "payout",
        "queue_if_low_balance": True,
        "reference_id": reference_id[:40],
        "narration": narration[:30],
    }
    idem = idempotency_key.replace("\n", "")[:36]
    async with httpx.AsyncClient(timeout=45.0) as client:
        r = await client.post(
            "https://api.razorpay.com/v1/payouts",
            json=payload,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
                "X-Payout-Idempotency": idem,
            },
        )
        if r.status_code >= 400:
            logger.warning("Razorpay payout create failed status=%s body=%s", r.status_code, r.text[:500])
        r.raise_for_status()
        return r.json()
