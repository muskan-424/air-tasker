"""Live WebSocket notification delivery (requires DB + migrations)."""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration


def _register_and_token(client, *, role: str) -> str:
    email = f"pytest_ws_{role.lower()}_{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass123!"
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert reg.status_code == 200, reg.text
    return reg.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_notifications_ws_receives_task_published_event(client, integration_env):
    _ = integration_env
    token = _register_and_token(client, role="POSTER")

    with client.websocket_connect(f"/api/notifications/ws?token={token}") as ws:
        ws.send_text("ping")
        assert ws.receive_json() == {"type": "pong"}

        draft = client.post(
            "/api/tasks/drafts",
            json={
                "raw_input": "Need plumbing fix in Indore today, budget 1500 INR",
                "language": "en",
            },
            headers=_auth_headers(token),
        )
        assert draft.status_code == 200, draft.text
        draft_id = draft.json()["id"]

        pub = client.post(f"/api/tasks/{draft_id}/publish", headers=_auth_headers(token))
        assert pub.status_code == 200, pub.text

        msg = ws.receive_json()
        assert msg["type"] == "notification"
        assert msg["title"] == "Task published"
        assert "task_id" in (msg.get("body") or "")
        assert msg["category"] == "TASK"
        assert msg["delivery_status"] == "delivered"
