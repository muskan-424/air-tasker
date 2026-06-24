def test_create_report_requires_target(client):
    client.post("/api/auth/register", json={"email": "reporter1@example.com", "password": "secret123", "role": "POSTER"})
    login = client.post("/api/auth/login", json={"email": "reporter1@example.com", "password": "secret123"})
    token = login.json()["access_token"]

    res = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={"category": "fraud", "reason": "Suspicious behaviour on platform"},
    )
    assert res.status_code == 400


def test_create_report_and_admin_queue(client):
    reporter_email = "reporter_queue@example.com"
    client.post("/api/auth/register", json={"email": reporter_email, "password": "secret123", "role": "POSTER"})
    reporter_login = client.post("/api/auth/login", json={"email": reporter_email, "password": "secret123"})
    reporter_token = reporter_login.json()["access_token"]

    target_email = "report_target@example.com"
    client.post("/api/auth/register", json={"email": target_email, "password": "secret123", "role": "TASKER"})
    target_login = client.post("/api/auth/login", json={"email": target_email, "password": "secret123"})
    target_token = target_login.json()["access_token"]
    target_me = client.get("/api/users/me", headers={"Authorization": f"Bearer {target_token}"})
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
    assert create.status_code == 201
    body = create.json()
    assert body["status"] == "OPEN"
    assert "report_id" in body

    denied = client.get("/api/reports/open", headers={"Authorization": f"Bearer {reporter_token}"})
    assert denied.status_code == 403

    admin_email = "admin_reports@example.com"
    client.post("/api/auth/register", json={"email": admin_email, "password": "secret123", "role": "ADMIN"})
    admin_login = client.post("/api/auth/login", json={"email": admin_email, "password": "secret123"})
    admin_token = admin_login.json()["access_token"]

    queue = client.get("/api/reports/open", headers={"Authorization": f"Bearer {admin_token}"})
    assert queue.status_code == 200
    items = queue.json()
    assert any(i["report_id"] == body["report_id"] for i in items)

    flags = client.get("/api/reports/trust-flags/active", headers={"Authorization": f"Bearer {admin_token}"})
    assert flags.status_code == 200
    assert isinstance(flags.json(), list)
