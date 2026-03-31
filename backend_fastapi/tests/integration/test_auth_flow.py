"""Requires PostgreSQL with schema applied (`alembic upgrade head`).

Run with: set RUN_INTEGRATION_TESTS=1 (PowerShell: $env:RUN_INTEGRATION_TESTS=1) then pytest tests/integration -q
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration


def test_register_and_login(client, integration_env):
    email = f"pytest_{uuid.uuid4().hex[:12]}@example.com"
    password = "TestPass123!"

    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "role": "POSTER"},
    )
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    assert token

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]
