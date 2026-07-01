import uuid


def _register(client, role: str) -> str:
    email = f"rating_{role.lower()}_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret123", "role": role},
    )
    assert reg.status_code == 200, reg.text
    login = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _publish_task(client, poster_token: str) -> str:
    draft = client.post(
        "/api/tasks/drafts",
        json={
            "raw_input": "Need electrical wiring repair in Dehradun PIN 110001, budget up to 2000 INR",
            "language": "en",
        },
        headers=_auth(poster_token),
    )
    assert draft.status_code == 200, draft.text
    publish = client.post(
        f"/api/tasks/{draft.json()['id']}/publish",
        headers=_auth(poster_token),
    )
    assert publish.status_code == 200, publish.text
    return publish.json()["id"]


def _complete_task_for_rating(client, poster_token: str, tasker_token: str, task_id: str) -> None:
    accept = client.post(
        f"/api/tasks/{task_id}/accept",
        json={"acknowledge_requirements": True, "acknowledgement": {"gear": "yes"}},
        headers=_auth(tasker_token),
    )
    assert accept.status_code == 200, accept.text
    escrow = client.post(f"/api/tasks/{task_id}/escrow/start", headers=_auth(poster_token))
    assert escrow.status_code == 200, escrow.text
    evidence = client.post(
        f"/api/tasks/{task_id}/evidence",
        json={
            "before_image_url": "https://example.com/before.jpg",
            "after_image_url": "https://example.com/after.jpg",
        },
        headers=_auth(tasker_token),
    )
    assert evidence.status_code == 200, evidence.text
    verify = client.post(f"/api/tasks/{task_id}/verify", headers=_auth(poster_token))
    assert verify.status_code == 200, verify.text
    release = client.post(f"/api/tasks/{task_id}/escrow/release", headers=_auth(poster_token))
    assert release.status_code == 200, release.text
    assert release.json()["status"] == "RELEASED"


def test_rate_task_after_escrow_release(client):
    poster_token = _register(client, "POSTER")
    tasker_token = _register(client, "TASKER")
    tasker_me = client.get("/api/users/me", headers=_auth(tasker_token))
    assert tasker_me.status_code == 200, tasker_me.text
    tasker_id = tasker_me.json()["id"]

    task_id = _publish_task(client, poster_token)
    _complete_task_for_rating(client, poster_token, tasker_token, task_id)

    too_early = client.post(
        f"/api/tasks/{task_id}/rate",
        headers=_auth(tasker_token),
        json={"score": 5, "comment": "Great poster"},
    )
    assert too_early.status_code == 403

    rate = client.post(
        f"/api/tasks/{task_id}/rate",
        headers=_auth(poster_token),
        json={"score": 5, "comment": "Excellent work, very professional."},
    )
    assert rate.status_code == 201, rate.text
    body = rate.json()
    assert body["score"] == 5
    assert body["ratee_id"] == tasker_id
    assert body["task_id"] == task_id

    duplicate = client.post(
        f"/api/tasks/{task_id}/rate",
        headers=_auth(poster_token),
        json={"score": 4},
    )
    assert duplicate.status_code == 409

    mine = client.get(f"/api/tasks/{task_id}/rating", headers=_auth(poster_token))
    assert mine.status_code == 200, mine.text
    assert mine.json()["rating_id"] == body["rating_id"]

    summary = client.get(f"/api/users/{tasker_id}/ratings-summary", headers=_auth(poster_token))
    assert summary.status_code == 200, summary.text
    summary_body = summary.json()
    assert summary_body["rating_count"] == 1
    assert summary_body["average_score"] == 5.0

    profile = client.get("/api/users/me/profile", headers=_auth(tasker_token))
    assert profile.status_code == 200, profile.text
    profile_body = profile.json()
    assert profile_body["rating_count"] == 1
    assert profile_body["rating_average"] == 5.0


def test_rate_task_before_release_rejected(client):
    poster_token = _register(client, "POSTER")
    tasker_token = _register(client, "TASKER")
    task_id = _publish_task(client, poster_token)

    accept = client.post(
        f"/api/tasks/{task_id}/accept",
        json={"acknowledge_requirements": True},
        headers=_auth(tasker_token),
    )
    assert accept.status_code == 200, accept.text

    rate = client.post(
        f"/api/tasks/{task_id}/rate",
        headers=_auth(poster_token),
        json={"score": 3},
    )
    assert rate.status_code == 409
