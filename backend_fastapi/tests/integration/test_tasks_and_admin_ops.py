from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration


def _register_and_token(client, *, role: str) -> tuple[str, str, str]:
    email = f"pytest_{role.lower()}_{uuid.uuid4().hex[:10]}@example.com"
    password = "TestPass123!"
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    return email, password, token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_and_publish_task(client, poster_token: str) -> str:
    draft = client.post(
        "/api/tasks/drafts",
        json={"raw_input": "Need AC repair in Dehradun with quick turnaround, budget up to 2000 INR", "language": "en"},
        headers=_auth_headers(poster_token),
    )
    assert draft.status_code == 200, draft.text
    draft_id = draft.json()["id"]

    publish = client.post(f"/api/tasks/{draft_id}/publish", headers=_auth_headers(poster_token))
    assert publish.status_code == 200, publish.text
    return publish.json()["id"]


def test_task_happy_path_with_escrow_release(client, integration_env):
    _ = integration_env
    _, _, poster_token = _register_and_token(client, role="POSTER")
    _, _, tasker_token = _register_and_token(client, role="TASKER")

    task_id = _create_and_publish_task(client, poster_token)

    feed = client.get("/api/tasks/feed", headers=_auth_headers(tasker_token))
    assert feed.status_code == 200, feed.text
    assert any(row["id"] == task_id for row in feed.json())

    accept = client.post(
        f"/api/tasks/{task_id}/accept",
        json={"acknowledge_requirements": True, "acknowledgement": {"gear": "yes"}},
        headers=_auth_headers(tasker_token),
    )
    assert accept.status_code == 200, accept.text

    escrow = client.post(f"/api/tasks/{task_id}/escrow/start", headers=_auth_headers(poster_token))
    assert escrow.status_code == 200, escrow.text
    assert escrow.json()["status"] in {"HELD", "RELEASE_ELIGIBLE", "RELEASED"}

    evidence = client.post(
        f"/api/tasks/{task_id}/evidence",
        json={
            "before_image_url": "https://example.com/before.jpg",
            "after_image_url": "https://example.com/after.jpg",
        },
        headers=_auth_headers(tasker_token),
    )
    assert evidence.status_code == 200, evidence.text

    verify = client.post(f"/api/tasks/{task_id}/verify", headers=_auth_headers(poster_token))
    assert verify.status_code == 200, verify.text
    assert verify.json()["status"] == "PASS"

    release = client.post(f"/api/tasks/{task_id}/escrow/release", headers=_auth_headers(poster_token))
    assert release.status_code == 200, release.text
    assert release.json()["status"] == "RELEASED"


def test_dispute_open_and_admin_resolve(client, integration_env):
    _ = integration_env
    _, _, poster_token = _register_and_token(client, role="POSTER")
    _, _, tasker_token = _register_and_token(client, role="TASKER")
    _, _, admin_token = _register_and_token(client, role="ADMIN")

    task_id = _create_and_publish_task(client, poster_token)
    accept = client.post(
        f"/api/tasks/{task_id}/accept",
        json={"acknowledge_requirements": True, "acknowledgement": {"ppe": "ok"}},
        headers=_auth_headers(tasker_token),
    )
    assert accept.status_code == 200, accept.text
    start_escrow = client.post(f"/api/tasks/{task_id}/escrow/start", headers=_auth_headers(poster_token))
    assert start_escrow.status_code == 200, start_escrow.text

    dispute = client.post(
        f"/api/tasks/{task_id}/disputes",
        json={"reason": "Work quality mismatch"},
        headers=_auth_headers(tasker_token),
    )
    assert dispute.status_code == 200, dispute.text
    dispute_id = dispute.json()["dispute_id"]
    assert dispute.json()["status"] == "OPEN"

    resolve = client.post(
        f"/api/tasks/disputes/{dispute_id}/resolve",
        json={"outcome": "cancel", "note": "Refund approved"},
        headers=_auth_headers(admin_token),
    )
    assert resolve.status_code == 200, resolve.text
    body = resolve.json()
    assert body["status"] == "RESOLVED"
    assert body["escrow_status"] == "CANCELLED"


def test_admin_notification_retry_and_metrics(client, integration_env):
    _ = integration_env
    _, _, admin_token = _register_and_token(client, role="ADMIN")

    queue_retry = client.post(
        "/api/admin/jobs/notifications/retry-failed",
        json={"limit": 10},
        headers=_auth_headers(admin_token),
    )
    assert queue_retry.status_code == 200, queue_retry.text
    assert queue_retry.json()["kind"] == "notifications.retry_failed"

    sync_retry = client.post(
        "/api/admin/jobs/notifications/retry-failed/sync",
        json={"limit": 10},
        headers=_auth_headers(admin_token),
    )
    assert sync_retry.status_code == 200, sync_retry.text
    assert "snapshot" in sync_retry.json()

    notification_metrics = client.get("/api/metrics/internal/notifications", headers=_auth_headers(admin_token))
    assert notification_metrics.status_code == 200, notification_metrics.text
    payload = notification_metrics.json()
    assert "by_status" in payload
    assert "retry_config" in payload
