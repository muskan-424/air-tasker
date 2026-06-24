"""Pytest config: set env before importing the FastAPI app (settings load at import time)."""

from __future__ import annotations

import asyncio
import os

# Mark test runs so the DB layer uses NullPool (avoids asyncpg pool teardown on closed loops).
os.environ["TESTING"] = "1"

# Quiet background loops during tests; avoid connecting to Pinecone/Gemini implicitly.
os.environ.setdefault("NOTIFICATION_RETRY_INTERVAL_SECONDS", "0")
os.environ.setdefault("RAG_REINDEX_INTERVAL_HOURS", "0")
os.environ.setdefault("USE_PINECONE_RAG", "false")
# Unless explicitly testing Redis notification fanout, keep tests in-process only.
if os.getenv("PYTEST_KEEP_REDIS") != "1":
    os.environ.pop("REDIS_URL", None)
# Avoid background Razorpay webhook table cleanup during unit tests (override .env).
os.environ["RAZORPAY_WEBHOOK_EVENTS_CLEANUP_INTERVAL_HOURS"] = "0"
# Deterministic drafts/chat in tests (do not call Gemini from developer .env).
os.environ["USE_MOCK_CHATBOT"] = "true"
os.environ.pop("GEMINI_API_KEY", None)

import pytest
from fastapi.testclient import TestClient

from app.db.session import engine
from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def dispose_async_engine_after_tests():
    """Close SQLAlchemy async pool after the suite (TestClient + asyncpg teardown)."""
    yield
    try:
        asyncio.run(engine.dispose())
    except RuntimeError:
        pass


@pytest.fixture
def integration_env():
    if os.getenv("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_INTEGRATION_TESTS=1 and ensure DATABASE_URL points at a migrated DB")
