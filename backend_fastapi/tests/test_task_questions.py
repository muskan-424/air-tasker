"""Public Q&A on open tasks (needs a migrated DB, like test_ratings)."""

import uuid


def _register(client, role: str) -> str:
    email = f"qa_{role.lower()}_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post("/api/auth/register", json={"email": email, "password": "secret123", "role": role})
    assert reg.status_code == 200, reg.text
    return reg.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _publish_task(client, poster_token: str) -> str:
    draft = client.post(
        "/api/tasks/drafts",
        json={"raw_input": "Need electrical wiring repair PIN 110001, budget up to 2000 INR", "language": "en"},
        headers=_auth(poster_token),
    )
    assert draft.status_code == 200, draft.text
    publish = client.post(f"/api/tasks/{draft.json()['id']}/publish", headers=_auth(poster_token))
    assert publish.status_code == 200, publish.text
    return publish.json()["id"]


def test_ask_and_answer_question(client):
    poster = _register(client, "POSTER")
    tasker = _register(client, "TASKER")
    task_id = _publish_task(client, poster)

    empty = client.get(f"/api/tasks/{task_id}/questions", headers=_auth(tasker))
    assert empty.status_code == 200
    assert empty.json() == []

    ask = client.post(
        f"/api/tasks/{task_id}/questions", json={"question": "Do you have the parts already?"}, headers=_auth(tasker)
    )
    assert ask.status_code == 201, ask.text
    body = ask.json()
    assert body["question"] == "Do you have the parts already?"
    assert body["answer"] is None

    # The poster cannot ask on their own task.
    forbidden = client.post(f"/api/tasks/{task_id}/questions", json={"question": "test"}, headers=_auth(poster))
    assert forbidden.status_code == 403

    # Only the poster can answer.
    cannot_answer = client.post(
        f"/api/tasks/{task_id}/questions/{body['id']}/answer",
        json={"answer": "Yes"},
        headers=_auth(tasker),
    )
    assert cannot_answer.status_code == 403

    answered = client.post(
        f"/api/tasks/{task_id}/questions/{body['id']}/answer",
        json={"answer": "Yes, I'll bring everything needed."},
        headers=_auth(poster),
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["answer"] == "Yes, I'll bring everything needed."
    assert answered.json()["answered_at"] is not None

    listing = client.get(f"/api/tasks/{task_id}/questions", headers=_auth(tasker)).json()
    assert len(listing) == 1
    assert listing[0]["answer"] == "Yes, I'll bring everything needed."


def test_questions_closed_once_task_is_assigned(client):
    poster = _register(client, "POSTER")
    tasker = _register(client, "TASKER")
    task_id = _publish_task(client, poster)

    offer = client.post(f"/api/tasks/{task_id}/offers", json={"amount": 1500}, headers=_auth(tasker))
    assert offer.status_code == 200, offer.text
    accept = client.post(
        f"/api/tasks/{task_id}/offers/{offer.json()['offer_id']}/accept", headers=_auth(poster)
    )
    assert accept.status_code == 200, accept.text

    other_tasker = _register(client, "TASKER")
    blocked = client.post(
        f"/api/tasks/{task_id}/questions", json={"question": "Still open?"}, headers=_auth(other_tasker)
    )
    assert blocked.status_code == 409
