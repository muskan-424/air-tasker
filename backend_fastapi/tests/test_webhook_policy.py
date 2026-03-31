import json

from app.core.config import settings


def test_webhook_rejected_in_production_without_secret(client):
    original_env = settings.environment
    original_secret = settings.razorpay_webhook_secret
    settings.environment = "production"
    settings.razorpay_webhook_secret = None
    try:
        r = client.post("/api/webhooks/razorpay", content=b"{}")
        assert r.status_code == 503
        assert "Webhook secret is required" in r.text
    finally:
        settings.environment = original_env
        settings.razorpay_webhook_secret = original_secret


def test_webhook_allows_dev_without_secret(client):
    original_env = settings.environment
    original_secret = settings.razorpay_webhook_secret
    settings.environment = "development"
    settings.razorpay_webhook_secret = None
    try:
        payload = {"event": "payment.failed"}
        r = client.post("/api/webhooks/razorpay", content=json.dumps(payload).encode("utf-8"))
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"
    finally:
        settings.environment = original_env
        settings.razorpay_webhook_secret = original_secret


def test_webhook_payout_downtime_ignored_no_escrow_query(client):
    """Global payout downtime events: no payout id lookup; no top-level id avoids dedupe insert."""
    original_env = settings.environment
    original_secret = settings.razorpay_webhook_secret
    settings.environment = "development"
    settings.razorpay_webhook_secret = None
    try:
        payload = {"event": "payout.downtime.started", "payload": {}}
        r = client.post("/api/webhooks/razorpay", content=json.dumps(payload).encode("utf-8"))
        assert r.status_code == 200
        assert r.json().get("note") == "payout_downtime_ignored"
    finally:
        settings.environment = original_env
        settings.razorpay_webhook_secret = original_secret


def test_webhook_refund_failed_logs_ok(client):
    """No top-level `id`: skips dedupe insert so this runs without razorpay_webhook_events table."""
    original_env = settings.environment
    original_secret = settings.razorpay_webhook_secret
    settings.environment = "development"
    settings.razorpay_webhook_secret = None
    try:
        payload = {
            "event": "refund.failed",
            "payload": {
                "refund": {
                    "entity": {
                        "id": "rfnd_fail_1",
                        "payment_id": "pay_x",
                    }
                }
            },
        }
        r = client.post("/api/webhooks/razorpay", content=json.dumps(payload).encode("utf-8"))
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json().get("note") == "refund_failed_logged"
    finally:
        settings.environment = original_env
        settings.razorpay_webhook_secret = original_secret
