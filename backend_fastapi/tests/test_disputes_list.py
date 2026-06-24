def test_list_open_disputes_endpoints(client):
    poster_email = "poster_dispute_list2@example.com"
    client.post("/api/auth/register", json={"email": poster_email, "password": "secret123", "role": "POSTER"})
    poster_login = client.post("/api/auth/login", json={"email": poster_email, "password": "secret123"})
    poster_token = poster_login.json()["access_token"]

    denied = client.get(
        "/api/tasks/disputes/open",
        headers={"Authorization": f"Bearer {poster_token}"},
    )
    assert denied.status_code == 403

    admin_email = "admin_dispute2@example.com"
    client.post("/api/auth/register", json={"email": admin_email, "password": "secret123", "role": "ADMIN"})
    admin_login = client.post("/api/auth/login", json={"email": admin_email, "password": "secret123"})
    admin_token = admin_login.json()["access_token"]

    ok = client.get(
        "/api/tasks/disputes/open",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ok.status_code == 200
    assert isinstance(ok.json(), list)
