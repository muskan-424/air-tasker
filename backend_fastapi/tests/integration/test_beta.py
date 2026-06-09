import pytest

pytestmark = pytest.mark.integration


def test_beta_feedback_submission(client, integration_env):
    _ = integration_env
    response = client.post(
        "/api/beta/feedback",
        json={
            "category": "support",
            "message": "Need help publishing a task in Dehradun PIN 248001",
            "email": "beta_user@example.com",
            "page_path": "/poster",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "received"
    assert body["feedback_id"]


def test_beta_kpis_requires_admin(client, integration_env):
    _ = integration_env
    denied = client.get("/api/beta/kpis")
    assert denied.status_code == 401

    email = "beta_admin_kpi@example.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "role": "ADMIN"},
    )
    login = client.post("/api/auth/login", json={"email": email, "password": "TestPass123!"})
    token = login.json()["access_token"]
    ok = client.get("/api/beta/kpis", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200
    payload = ok.json()
    assert "accept_rate" in payload
    assert "dispute_rate" in payload
    assert "beta_categories" in payload
