import pytest

pytestmark = pytest.mark.integration


def test_payout_status_endpoints(client):
    poster_email = "poster_payout2@example.com"
    client.post("/api/auth/register", json={"email": poster_email, "password": "secret123", "role": "POSTER"})
    poster_login = client.post("/api/auth/login", json={"email": poster_email, "password": "secret123"})
    poster_token = poster_login.json()["access_token"]

    denied = client.get(
        "/api/payments/razorpay/payout/status",
        headers={"Authorization": f"Bearer {poster_token}"},
    )
    assert denied.status_code == 403

    tasker_email = "tasker_payout2@example.com"
    client.post("/api/auth/register", json={"email": tasker_email, "password": "secret123", "role": "TASKER"})
    tasker_login = client.post("/api/auth/login", json={"email": tasker_email, "password": "secret123"})
    tasker_token = tasker_login.json()["access_token"]

    ok = client.get(
        "/api/payments/razorpay/payout/status",
        headers={"Authorization": f"Bearer {tasker_token}"},
    )
    assert ok.status_code == 200
    data = ok.json()
    assert data["registered"] is False
    assert data["fund_account_id"] is None
