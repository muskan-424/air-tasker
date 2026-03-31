import hashlib
import hmac

from app.services.razorpay_service import verify_webhook_signature


def test_verify_webhook_signature_ok():
    body = b'{"event":"payment.captured"}'
    secret = "whsec_test"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, sig, secret) is True


def test_verify_webhook_signature_rejects_tamper():
    body = b'{"event":"payment.captured"}'
    secret = "whsec_test"
    assert verify_webhook_signature(body, "deadbeef", secret) is False
