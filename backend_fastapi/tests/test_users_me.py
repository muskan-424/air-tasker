def test_get_me_requires_auth(client):
    response = client.get("/api/users/me")
    assert response.status_code == 401
