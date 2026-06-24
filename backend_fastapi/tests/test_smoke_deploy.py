import uuid


def test_webhooks_health_endpoint(client):
    response = client.get("/api/health/webhooks")
    assert response.status_code == 200
    body = response.json()
    assert "razorpay_webhook_secret_configured" in body
    assert body["razorpay_webhook_path"] == "/api/webhooks/razorpay"


def test_smoke_task_flow_via_test_client(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    email = f"smoke_unit_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": "SmokePass123!", "role": "POSTER"},
    )
    assert reg.status_code == 200
    token = reg.json()["access_token"]

    draft = client.post(
        "/api/tasks/drafts",
        json={"raw_input": "Unit smoke electrical repair PIN 110001", "language": "en"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert draft.status_code == 200
    draft_id = draft.json()["id"]

    pub = client.post(
        f"/api/tasks/{draft_id}/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pub.status_code == 200
    assert pub.json()["status"].upper() == "PUBLISHED"

    denied = client.get(
        "/api/payments/razorpay/payout/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 403
