import uuid

import pytest


def _register(client, role: str) -> str:
    email = f"report_{role.lower()}_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret123", "role": role},
    )
    assert reg.status_code == 200, reg.text
    login = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_create_report_requires_target(client):
    token = _register(client, "POSTER")
    res = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={"category": "fraud", "reason": "Suspicious behaviour on platform"},
    )
    assert res.status_code == 400


def test_create_report_and_admin_queue(client):
    reporter_token = _register(client, "POSTER")
    target_token = _register(client, "TASKER")
    target_me = client.get("/api/users/me", headers={"Authorization": f"Bearer {target_token}"})
    assert target_me.status_code == 200, target_me.text
    target_id = target_me.json()["id"]

    create = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {reporter_token}"},
        json={
            "reported_user_id": target_id,
            "category": "fraud",
            "reason": "User asked for payment outside escrow repeatedly.",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["status"] == "OPEN"
    assert "report_id" in body

    denied = client.get("/api/reports/open", headers={"Authorization": f"Bearer {reporter_token}"})
    assert denied.status_code == 403

    admin_token = _register(client, "ADMIN")
    queue = client.get("/api/reports/open", headers={"Authorization": f"Bearer {admin_token}"})
    assert queue.status_code == 200, queue.text
    items = queue.json()
    assert any(i["report_id"] == body["report_id"] for i in items)

    flags = client.get("/api/reports/trust-flags/active", headers={"Authorization": f"Bearer {admin_token}"})
    assert flags.status_code == 200, flags.text
    assert isinstance(flags.json(), list)
