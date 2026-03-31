import hashlib
import hmac
from app.core.config import settings
from app.services.kyc_webhook_service import verify_kyc_webhook_signature


def test_verify_kyc_webhook_signature_roundtrip():
    body = b'{"x": 1}'
    secret = "test_secret"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_kyc_webhook_signature(body, sig, secret)
    assert not verify_kyc_webhook_signature(body, "bad", secret)


def test_kyc_webhook_rejected_in_production_without_secret(client):
    original_env = settings.environment
    original_secret = settings.kyc_webhook_secret
    settings.environment = "production"
    settings.kyc_webhook_secret = None
    try:
        r = client.post("/api/webhooks/kyc", content=b"{}")
        assert r.status_code == 503
        assert "KYC webhook secret" in r.text
    finally:
        settings.environment = original_env
        settings.kyc_webhook_secret = original_secret
