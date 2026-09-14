"""Offers, cancellation, service fees, and dual-role accounts (needs a migrated DB, like test_ratings)."""

import uuid

import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def _fixed_fees(monkeypatch):
    monkeypatch.setattr(settings, "poster_service_fee_percent", 5.0)
    monkeypatch.setattr(settings, "tasker_service_fee_percent", 10.0)
    monkeypatch.setattr(settings, "service_fee_min_inr", 10.0)
    monkeypatch.setattr(settings, "cancellation_fee_percent", 10.0)
    monkeypatch.setattr(settings, "task_instant_accept_enabled", False)


def _register(client, role: str) -> str:
    email = f"market_{role.lower()}_{uuid.uuid4().hex[:10]}@example.com"
    reg = client.post("/api/auth/register", json={"email": email, "password": "secret123", "role": role})
    assert reg.status_code == 200, reg.text
    return reg.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _me_id(client, token: str) -> str:
    return client.get("/api/users/me", headers=_auth(token)).json()["id"]


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


def _offer(client, token: str, task_id: str, amount: float, message: str | None = None):
    return client.post(
        f"/api/tasks/{task_id}/offers",
        json={"amount": amount, "message": message},
        headers=_auth(token),
    )


def test_offers_poster_picks_one_and_others_are_declined(client):
    poster = _register(client, "POSTER")
    tasker_a = _register(client, "TASKER")
    tasker_b = _register(client, "TASKER")
    task_id = _publish_task(client, poster)

    offer_a = _offer(client, tasker_a, task_id, 1800, "Licensed electrician")
    assert offer_a.status_code == 200, offer_a.text
    offer_b = _offer(client, tasker_b, task_id, 1500)
    assert offer_b.status_code == 200, offer_b.text
    assert offer_b.json()["fees"]["tasker_payout"] == "1350.00"

    # Updating keeps a single offer per tasker.
    updated = _offer(client, tasker_a, task_id, 1700, "Licensed electrician, can come today")
    assert updated.status_code == 200
    assert updated.json()["offer_id"] == offer_a.json()["offer_id"]
    assert updated.json()["amount"] == "1700.00"

    poster_view = client.get(f"/api/tasks/{task_id}/offers", headers=_auth(poster))
    assert poster_view.status_code == 200
    assert [o["amount"] for o in poster_view.json()] == ["1500.00", "1700.00"]  # cheapest first

    tasker_view = client.get(f"/api/tasks/{task_id}/offers", headers=_auth(tasker_b))
    assert [o["offer_id"] for o in tasker_view.json()] == [offer_b.json()["offer_id"]]

    # Only the poster may accept.
    forbidden = client.post(
        f"/api/tasks/{task_id}/offers/{offer_b.json()['offer_id']}/accept", headers=_auth(tasker_b)
    )
    assert forbidden.status_code == 403

    accepted = client.post(
        f"/api/tasks/{task_id}/offers/{offer_b.json()['offer_id']}/accept", headers=_auth(poster)
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["task_status"] == "ACCEPTED"
    assert accepted.json()["offer"]["status"] == "ACCEPTED"

    after = {o["offer_id"]: o["status"] for o in client.get(f"/api/tasks/{task_id}/offers", headers=_auth(poster)).json()}
    assert after[offer_a.json()["offer_id"]] == "DECLINED"

    detail = client.get(f"/api/tasks/{task_id}", headers=_auth(poster)).json()
    assert detail["tasker_id"] == _me_id(client, tasker_b)
    assert detail["scope"]["status"] == "ACCEPTED"
    assert detail["scope"]["agreed_price"] == "1500.00"
    assert detail["fees"]["poster_total"] == "1575.00"

    # Late offers and a second accept are rejected.
    assert _offer(client, tasker_a, task_id, 1400).status_code == 409
    again = client.post(
        f"/api/tasks/{task_id}/offers/{offer_a.json()['offer_id']}/accept", headers=_auth(poster)
    )
    assert again.status_code == 409

    # Escrow charges the offer price plus the poster fee and records the breakdown.
    escrow = client.post(f"/api/tasks/{task_id}/escrow/start", headers=_auth(poster))
    assert escrow.status_code == 200, escrow.text
    assert escrow.json()["amount"] == "1575.00"
    assert escrow.json()["fees"]["tasker_payout"] == "1350.00"


def test_offer_validation(client):
    poster = _register(client, "POSTER")
    tasker = _register(client, "TASKER")
    task_id = _publish_task(client, poster)

    assert _offer(client, poster, task_id, 1500).status_code == 403  # own task
    assert _offer(client, tasker, task_id, 5).status_code == 400  # below minimum

    offer = _offer(client, tasker, task_id, 1500)
    withdraw = client.post(
        f"/api/tasks/{task_id}/offers/{offer.json()['offer_id']}/withdraw", headers=_auth(tasker)
    )
    assert withdraw.status_code == 200
    assert withdraw.json()["status"] == "WITHDRAWN"
    assert client.get(f"/api/tasks/{task_id}/offers", headers=_auth(poster)).json() == []

    cannot_accept = client.post(
        f"/api/tasks/{task_id}/offers/{offer.json()['offer_id']}/accept", headers=_auth(poster)
    )
    assert cannot_accept.status_code == 409

    # Re-offering revives the same row as pending.
    revived = _offer(client, tasker, task_id, 1600)
    assert revived.json()["offer_id"] == offer.json()["offer_id"]
    assert revived.json()["status"] == "PENDING"


def test_instant_accept_disabled_by_default(client):
    poster = _register(client, "POSTER")
    tasker = _register(client, "TASKER")
    task_id = _publish_task(client, poster)
    resp = client.post(f"/api/tasks/{task_id}/accept", json={"acknowledge_requirements": True}, headers=_auth(tasker))
    assert resp.status_code == 409
    assert "offer" in resp.json()["detail"].lower()


def test_poster_cancels_open_task_for_free(client):
    poster = _register(client, "POSTER")
    tasker = _register(client, "TASKER")
    task_id = _publish_task(client, poster)
    offer = _offer(client, tasker, task_id, 1500)

    assert client.post(f"/api/tasks/{task_id}/cancel", json={}, headers=_auth(tasker)).status_code == 403

    cancel = client.post(f"/api/tasks/{task_id}/cancel", json={"reason": "Fixed it myself"}, headers=_auth(poster))
    assert cancel.status_code == 200, cancel.text
    body = cancel.json()
    assert body["cancelled_by"] == "POSTER"
    assert body["previous_status"] == "PUBLISHED"
    assert body["fee_amount"] == "0.00"
    assert body["refund_status"] is None

    tasker_offer = client.get(f"/api/tasks/{task_id}/offers", headers=_auth(tasker)).json()[0]
    assert tasker_offer["offer_id"] == offer.json()["offer_id"]
    assert tasker_offer["status"] == "DECLINED"

    again = client.post(f"/api/tasks/{task_id}/cancel", json={}, headers=_auth(poster))
    assert again.status_code == 409


def _assigned_task(client, amount: float = 1500):
    poster = _register(client, "POSTER")
    tasker = _register(client, "TASKER")
    task_id = _publish_task(client, poster)
    offer = _offer(client, tasker, task_id, amount)
    accepted = client.post(f"/api/tasks/{task_id}/offers/{offer.json()['offer_id']}/accept", headers=_auth(poster))
    assert accepted.status_code == 200, accepted.text
    return poster, tasker, task_id


def test_poster_cancel_after_assignment_keeps_fee_from_refund(client):
    poster, _tasker, task_id = _assigned_task(client)
    escrow = client.post(f"/api/tasks/{task_id}/escrow/start", headers=_auth(poster))
    assert escrow.json()["amount"] == "1575.00"

    cancel = client.post(f"/api/tasks/{task_id}/cancel", json={"reason": "Plans changed"}, headers=_auth(poster))
    assert cancel.status_code == 200, cancel.text
    body = cancel.json()
    assert body["cancelled_by"] == "POSTER"
    assert body["fee_amount"] == "150.00"
    assert body["refund_amount"] == "1425.00"
    assert body["refund_status"] == "not_captured"  # no Razorpay payment in tests

    detail = client.get(f"/api/tasks/{task_id}", headers=_auth(poster)).json()
    assert detail["status"] == "CANCELLED"
    assert detail["escrow_status"] == "CANCELLED"
    assert detail["cancelled_by"] == "POSTER"


def test_tasker_cancel_refunds_poster_in_full(client):
    poster, tasker, task_id = _assigned_task(client)
    client.post(f"/api/tasks/{task_id}/escrow/start", headers=_auth(poster))

    cancel = client.post(f"/api/tasks/{task_id}/cancel", json={"reason": "Sick"}, headers=_auth(tasker))
    assert cancel.status_code == 200, cancel.text
    body = cancel.json()
    assert body["cancelled_by"] == "TASKER"
    assert body["fee_amount"] == "150.00"
    assert body["refund_amount"] == "1575.00"


def test_cannot_cancel_verified_work(client):
    poster, tasker, task_id = _assigned_task(client)
    client.post(f"/api/tasks/{task_id}/escrow/start", headers=_auth(poster))
    client.post(
        f"/api/tasks/{task_id}/evidence",
        json={"before_image_url": "https://example.com/b.jpg", "after_image_url": "https://example.com/a.jpg"},
        headers=_auth(tasker),
    )
    verify = client.post(f"/api/tasks/{task_id}/verify", headers=_auth(poster))
    assert verify.json()["status"] == "PASS"

    cancel = client.post(f"/api/tasks/{task_id}/cancel", json={}, headers=_auth(poster))
    assert cancel.status_code == 409


def test_escrow_requires_assigned_tasker(client):
    poster = _register(client, "POSTER")
    task_id = _publish_task(client, poster)
    resp = client.post(f"/api/tasks/{task_id}/escrow/start", headers=_auth(poster))
    assert resp.status_code == 409


def test_one_account_can_post_and_work(client):
    alice = _register(client, "POSTER")
    bob = _register(client, "POSTER")

    # A poster-mode account can still make offers on someone else's task.
    bobs_task = _publish_task(client, bob)
    offer = _offer(client, alice, bobs_task, 1200)
    assert offer.status_code == 200, offer.text

    alices_task = _publish_task(client, alice)
    mine = client.get("/api/tasks/mine", headers=_auth(alice)).json()
    relations = {row["id"]: row["my_relation"] for row in mine}
    assert relations[alices_task] == "poster"
    assert relations[bobs_task] == "offer"

    working = client.get("/api/tasks/mine?view=working", headers=_auth(alice)).json()
    assert [row["id"] for row in working] == [bobs_task]

    switched = client.put("/api/users/me/mode", json={"mode": "TASKER"}, headers=_auth(alice))
    assert switched.status_code == 200, switched.text
    assert switched.json()["role"] == "TASKER"

    bad = client.put("/api/users/me/mode", json={"mode": "ADMIN"}, headers=_auth(alice))
    assert bad.status_code == 422

    admin = _register(client, "ADMIN")
    assert client.put("/api/users/me/mode", json={"mode": "POSTER"}, headers=_auth(admin)).status_code == 403


def test_fee_quote(client):
    token = _register(client, "POSTER")
    quote = client.get("/api/tasks/fees/quote?price=2000", headers=_auth(token))
    assert quote.status_code == 200, quote.text
    assert quote.json() == {
        "task_price": "2000.00",
        "poster_fee": "100.00",
        "poster_total": "2100.00",
        "tasker_fee": "200.00",
        "tasker_payout": "1800.00",
    }


def test_chat_assistant_apply_makes_an_offer(client):
    poster = _register(client, "POSTER")
    tasker = _register(client, "TASKER")
    task_id = _publish_task(client, poster)

    resp = client.post(
        "/api/chat/agent",
        json={"message": f"apply to task {task_id} for 1650 rupees"},
        headers=_auth(tasker),
    )
    assert resp.status_code == 200, resp.text
    assert "1650" in resp.json()["reply"]

    offers = client.get(f"/api/tasks/{task_id}/offers", headers=_auth(poster)).json()
    assert len(offers) == 1
    assert offers[0]["amount"] == "1650.00"
    assert offers[0]["status"] == "PENDING"
    assert client.get(f"/api/tasks/{task_id}", headers=_auth(poster)).json()["status"] == "PUBLISHED"
