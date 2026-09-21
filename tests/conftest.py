"""
EphemeralShield — Shared Test Configuration & Fixtures.

This module provides pytest fixtures used across ALL test types.
Fixtures are pytest's dependency injection mechanism for tests —
they set up preconditions and clean up after tests automatically.

WHY conftest.py?
  pytest automatically discovers and loads conftest.py files.
  Any fixture defined here is available to all tests in this directory
  and its subdirectories WITHOUT importing it. This is a pytest convention.

Architecture:
  tests/conftest.py       — Shared fixtures (settings, clients)
  tests/unit/             — Fast tests, no Docker services needed
  tests/integration/      — Tests against real databases (Docker required)
  tests/e2e/              — Full workflow tests through the API
"""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ephemeralshield.api.app import create_app
from ephemeralshield.settings import Settings


@pytest.fixture
def test_settings() -> Settings:
    """
    Create test-specific settings.

    WHY override settings in tests?
      Tests should NOT depend on the developer's .env file.
      Using hardcoded test values makes tests deterministic and reproducible.

    WHY not mock settings?
      Mocking hides bugs. If a setting name changes, mocks silently succeed
      while the real code breaks. Using the actual Settings class with test
      values catches these issues.
    """
    return Settings(
        broker_db_url=(
            "postgresql+psycopg://ephemeralshield:ephemeralshield_dev"
            "@localhost:5433/ephemeralshield"
        ),
        redis_url="redis://localhost:6379/0",
        lease_default_ttl_seconds=1800,
        lease_max_ttl_seconds=7200,
        environment="development",
        log_level="DEBUG",
        app_host="127.0.0.1",
        app_port=8000,
        _env_file=None,  # type: ignore[call-arg]  # Don't read .env in tests
    )


@pytest.fixture
def app() -> FastAPI:
    """
    Create a fresh FastAPI application for testing.

    Each test gets its own app instance — no state leaks between tests.
    """
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP test client.

    WHY httpx.AsyncClient instead of FastAPI's TestClient?
      TestClient uses requests (sync) under the hood. AsyncClient uses httpx
      and communicates with the ASGI app directly — no HTTP server needed,
      no port binding, and it supports async test functions natively.

    WHY ASGITransport?
      It connects httpx directly to the FastAPI ASGI app in-process.
      Requests never leave the process — they're routed internally.
      This is faster than TestClient and allows async/await in tests.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
