"""
EphemeralShield — Health Endpoint Unit Tests.

These tests verify the health check endpoints WITHOUT requiring Docker
services. They use FastAPI's async test client to make in-process requests.

What's tested:
  - /health/live returns 200 with no dependencies (liveness)
  - /health/ready returns 200 when database is reachable (readiness)
  - /health/ready returns 503 when database is unreachable

WHY test health endpoints?
  Health endpoints are the first thing you check when debugging production
  issues. If they're wrong (e.g., liveness checks the database), you get
  cascading restarts that make outages worse. These tests catch that early.
"""

from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from ephemeralshield.api.app import create_app


class TestLiveness:
    """Tests for GET /health/live — process liveness check."""

    async def test_liveness_returns_ok(self) -> None:
        """Liveness endpoint should always return 200 with {"status": "ok"}.

        This endpoint has NO dependencies — it proves the Python process
        can handle HTTP requests. If this fails, the process is broken.
        """
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_liveness_does_not_require_database(self) -> None:
        """Liveness should succeed even if the database is completely broken.

        WHY? If liveness depends on the database, a DB outage causes the
        orchestrator to restart the API container. Restarting doesn't fix
        the database — it just adds restart storms to the outage.
        """
        # The liveness endpoint doesn't inject any dependencies,
        # so it works even when app.state has no session_factory.
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/live")

        assert response.status_code == 200


class TestReadiness:
    """Tests for GET /health/ready — service readiness check."""

    async def test_readiness_returns_ready_when_db_available(self) -> None:
        """Readiness should return 200 when the database is reachable.

        We mock the database session to simulate a successful connection.
        Integration tests (Phase 2+) will test against real PostgreSQL.
        """
        app = create_app()

        # Create a mock session that successfully executes SELECT 1
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Create a mock session factory
        mock_factory = AsyncMock(return_value=mock_session)
        mock_factory.__aenter__ = mock_session.__aenter__
        mock_factory.__aexit__ = mock_session.__aexit__

        # Inject mock into app state
        from ephemeralshield.settings import Settings

        app.state.session_factory = lambda: mock_session
        app.state.settings = Settings(_env_file=None)  # type: ignore[call-arg]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"

    async def test_readiness_returns_503_when_db_unavailable(self) -> None:
        """Readiness should return 503 when the database is unreachable.

        This simulates a database outage. The load balancer should stop
        sending traffic to this instance.
        """
        from sqlalchemy.exc import OperationalError

        app = create_app()

        # Create a mock session that raises an error on execute
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=OperationalError("connection refused", {}, Exception())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        from ephemeralshield.settings import Settings

        app.state.session_factory = lambda: mock_session
        app.state.settings = Settings(_env_file=None)  # type: ignore[call-arg]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["database"] == "unreachable"

    async def test_readiness_does_not_expose_sensitive_info(self) -> None:
        """Readiness response must NOT contain database URLs, versions, or pool stats.

        This is a security requirement — an attacker querying /health/ready
        should not learn anything about the infrastructure.
        """
        app = create_app()

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        from ephemeralshield.settings import Settings

        app.state.session_factory = lambda: mock_session
        app.state.settings = Settings(_env_file=None)  # type: ignore[call-arg]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")

        data = response.json()
        response_text = str(data)

        # Should NOT contain any of these:
        assert "postgresql" not in response_text.lower()
        assert "password" not in response_text.lower()
        assert "5432" not in response_text
        assert "5433" not in response_text
        assert "ephemeralshield_dev" not in response_text
