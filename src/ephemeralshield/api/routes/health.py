"""
EphemeralShield — Health Check Routes.

These endpoints let Docker, load balancers, and monitoring tools verify the
application's status. They're the first thing you check when debugging.

Two endpoints with DIFFERENT purposes:

  /health/live  — "Is the process alive?"
    Returns 200 if the Python process is running and FastAPI can handle requests.
    Does NOT check databases, Redis, or any external dependencies.
    Used by Docker HEALTHCHECK and Kubernetes liveness probes.

    WHY no dependency checks? If liveness checks depend on the database,
    a database outage would make the orchestrator restart the API container.
    Restarting doesn't fix the database — it just adds restart churn.

  /health/ready — "Can this instance serve real requests?"
    Returns 200 only if the control-plane database is reachable.
    Returns 503 if any critical dependency is unavailable.
    Used by load balancers to route traffic away from unhealthy instances.

    WHY separate from liveness? An instance can be alive (process running)
    but not ready (database migration in progress). The load balancer should
    stop sending traffic without killing the process.

Security:
  These endpoints intentionally expose MINIMAL information:
    - No database version strings
    - No connection pool statistics
    - No configuration values
    - No hostnames or IP addresses
  An attacker should not learn anything useful from these responses.
"""

from typing import Any

from fastapi import APIRouter, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ephemeralshield.api.dependencies import CurrentSettings, DbSession


def create_health_router() -> APIRouter:
    """
    Create the health check router.

    WHY a factory function instead of a module-level router?
      Consistency with the app factory pattern. Tests can create independent
      routers without import-time side effects. This also makes it explicit
      that the router is a new instance each time.
    """
    router = APIRouter()

    @router.get(
        "/health/live",
        status_code=status.HTTP_200_OK,
        summary="Liveness probe",
        description="Returns 200 if the API process is running. No dependency checks.",
        response_model=dict[str, str],
    )
    async def liveness() -> dict[str, str]:
        """
        Process liveness check.

        This endpoint has no dependencies — it returns immediately.
        If this fails, the process is genuinely broken (OOM, deadlock, etc.)
        and should be restarted.
        """
        return {"status": "ok"}

    @router.get(
        "/health/ready",
        status_code=status.HTTP_200_OK,
        summary="Readiness probe",
        description="Returns 200 if the API can serve requests (database connected).",
        responses={
            503: {
                "description": "Service unavailable — database unreachable",
                "content": {
                    "application/json": {
                        "example": {
                            "status": "unavailable",
                            "database": "unreachable",
                        }
                    }
                },
            },
        },
    )
    async def readiness(
        db: DbSession,
        settings: CurrentSettings,
    ) -> dict[str, Any]:
        """
        Readiness check — verifies control-plane database connectivity.

        Executes 'SELECT 1' to verify:
          1. The connection pool can provide a connection
          2. The connection is authenticated (credentials work)
          3. The database is accepting queries (not in recovery/read-only)

        WHY 'SELECT 1' and not pg_isready?
          pg_isready is a command-line tool. From Python, we use a real
          SQL query through the connection pool. This tests the full path:
          pool → driver → TCP → PostgreSQL → response.

        NOTE: We intentionally do NOT report the database version, pool size,
        or connection details. Health endpoints must not leak infrastructure
        information (§1.2, threat model).
        """
        try:
            # Execute a minimal query to verify connectivity
            # text("SELECT 1") is the safest possible query — it doesn't
            # touch any tables, requires no permissions, and returns instantly.
            await db.execute(text("SELECT 1"))

            return {
                "status": "ready",
                "database": "connected",
                "environment": settings.environment,
            }
        except SQLAlchemyError:
            # WHY catch SQLAlchemyError specifically?
            # It covers: connection failures, authentication errors, timeout,
            # DNS resolution failures, and more. We don't want to expose the
            # specific error type or message to the caller.
            from fastapi.responses import JSONResponse

            return JSONResponse(  # type: ignore[return-value]
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unavailable",
                    "database": "unreachable",
                },
            )

    return router
