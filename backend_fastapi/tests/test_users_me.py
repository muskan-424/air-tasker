def test_get_me_requires_auth(client):
    response = client.get("/api/users/me")
    assert response.status_code == 401


def test_get_me_returns_account(client):
    email = "me_test@example.com"
    client.post("/api/auth/register", json={"email": email, "password": "secret123", "role": "POSTER"})
    login = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    token = login.json()["access_token"]
    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "POSTER"
    assert data["email_verified_at"] is None
