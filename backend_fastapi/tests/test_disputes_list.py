import uuid


def _register(client, role: str) -> str:
    email = f"dispute_{role.lower()}_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret123", "role": role},
    )
    assert reg.status_code == 200, reg.text
    login = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_list_open_disputes_endpoints(client):
    poster_token = _register(client, "POSTER")

    denied = client.get(
        "/api/tasks/disputes/open",
        headers={"Authorization": f"Bearer {poster_token}"},
    )
    assert denied.status_code == 403

    admin_token = _register(client, "ADMIN")

    ok = client.get(
        "/api/tasks/disputes/open",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ok.status_code == 200
    assert isinstance(ok.json(), list)
