"""Feed filtering for remote tasks and location_type (needs a migrated DB, like test_ratings).

Task text stays in the closed-beta electrical/plumbing/cleaning categories (see
`app.core.config.Settings.beta_categories`) so publishing isn't rejected by beta gating.
"""

import uuid


def _register(client, role: str) -> str:
    email = f"feed_{role.lower()}_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post("/api/auth/register", json={"email": email, "password": "secret123", "role": role})
    assert reg.status_code == 200, reg.text
    return reg.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _publish(client, poster_token: str, raw_input: str) -> str:
    draft = client.post(
        "/api/tasks/drafts", json={"raw_input": raw_input, "language": "en"}, headers=_auth(poster_token)
    )
    assert draft.status_code == 200, draft.text
    publish = client.post(f"/api/tasks/{draft.json()['id']}/publish", headers=_auth(poster_token))
    assert publish.status_code == 200, publish.text
    return publish.json()["id"]


def test_remote_task_visible_without_matching_service_pin(client):
    poster = _register(client, "POSTER")
    tasker = _register(client, "TASKER")

    profile = client.put(
        "/api/users/me/profile", json={"service_pin_codes": ["560001"]}, headers=_auth(tasker)
    )
    assert profile.status_code == 200, profile.text

    remote_task = _publish(client, poster, "remote electrical consultation over video call, budget 1500")
    local_task = _publish(client, poster, "electrical repair PIN 110001 budget 900")

    feed = client.get("/api/tasks/feed", headers=_auth(tasker))
    assert feed.status_code == 200, feed.text
    ids = {row["id"] for row in feed.json()}
    assert remote_task in ids
    assert local_task not in ids  # 110001 isn't in the tasker's service area


def test_location_type_filter(client):
    # Remote tasks are visible marketplace-wide, so other tests' remote tasks may also appear in
    # these feeds — assert membership/exclusion for this test's own tasks, not an exact set.
    poster = _register(client, "POSTER")
    tasker = _register(client, "TASKER")
    client.put("/api/users/me/profile", json={"service_pin_codes": ["110001"]}, headers=_auth(tasker))

    remote_task = _publish(client, poster, "remote electrical consultation over video call, budget 1200")
    local_task = _publish(client, poster, "electrical repair PIN 110001 budget 900")

    remote_only = client.get("/api/tasks/feed?location_type=REMOTE", headers=_auth(tasker))
    assert remote_only.status_code == 200
    remote_ids = {row["id"] for row in remote_only.json()}
    assert remote_task in remote_ids
    assert local_task not in remote_ids

    in_person_only = client.get("/api/tasks/feed?location_type=IN_PERSON", headers=_auth(tasker))
    in_person_ids = {row["id"] for row in in_person_only.json()}
    assert local_task in in_person_ids
    assert remote_task not in in_person_ids


def test_tasker_with_no_service_pins_still_sees_remote_tasks(client):
    poster = _register(client, "POSTER")
    tasker = _register(client, "TASKER")  # no service_pin_codes set

    remote_task = _publish(client, poster, "remote electrical consultation over video call, budget 500")

    feed = client.get("/api/tasks/feed", headers=_auth(tasker))
    assert feed.status_code == 200
    assert remote_task in {row["id"] for row in feed.json()}
