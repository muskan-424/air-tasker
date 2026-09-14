import uuid

from app.services.phone_utils import normalize_india_phone


def test_normalize_india_phone_variants():
    assert normalize_india_phone("9876543210") == "9876543210"
    assert normalize_india_phone("+91 98765 43210") == "9876543210"
    assert normalize_india_phone("919876543210") == "9876543210"
    assert normalize_india_phone("09876543210") == "9876543210"


def test_normalize_india_phone_rejects_invalid():
    import pytest

    with pytest.raises(ValueError):
        normalize_india_phone("12345")
    with pytest.raises(ValueError):
        normalize_india_phone("1234567890")  # doesn't start 6-9


def _register(client, role: str = "POSTER") -> str:
    email = f"phoneotp_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post("/api/auth/register", json={"email": email, "password": "secret123", "role": role})
    assert reg.status_code == 200, reg.text
    return reg.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_phone_otp_request_requires_phone_first_time(client):
    token = _register(client)
    resp = client.post("/api/verification/phone/request-otp", json={}, headers=_auth(token))
    assert resp.status_code == 400
    assert "phone" in resp.json()["detail"].lower()


def test_phone_otp_full_flow(client, monkeypatch):
    from app.services import otp_service

    captured = {}

    async def fake_send_sms(phone, body):
        captured["phone"] = phone
        code = "".join(ch for ch in body if ch.isdigit())[:6]
        captured["code"] = code
        return "stub"

    monkeypatch.setattr(otp_service, "send_sms", fake_send_sms)

    token = _register(client)
    req = client.post("/api/verification/phone/request-otp", json={"phone": "9876543210"}, headers=_auth(token))
    assert req.status_code == 200, req.text
    assert req.json()["phone"] == "9876543210"
    assert captured["phone"] == "9876543210"

    bad = client.post("/api/verification/phone/verify", json={"code": "000000"}, headers=_auth(token))
    assert bad.status_code == 400

    ok = client.post("/api/verification/phone/verify", json={"code": captured["code"]}, headers=_auth(token))
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "verified"

    already = client.post("/api/verification/phone/request-otp", json={}, headers=_auth(token))
    assert already.status_code == 400
    assert "already verified" in already.json()["detail"].lower()


def test_phone_otp_rejects_invalid_number(client):
    token = _register(client)
    resp = client.post("/api/verification/phone/request-otp", json={"phone": "12345"}, headers=_auth(token))
    assert resp.status_code == 400
