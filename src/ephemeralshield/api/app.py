"""
EphemeralShield — FastAPI Application Factory.

This module creates and configures the FastAPI application instance.

WHY an application factory (create_app function) instead of a global `app = FastAPI()`?
  1. Testability — tests can create fresh app instances with test-specific config
  2. Configuration — different environments (dev/staging/prod) get different settings
  3. Uvicorn --factory — supports lazy initialization, avoiding import side effects
  4. Multiple workers — each Uvicorn worker calls create_app() independently

The factory pattern is a well-established practice in Python web frameworks
(Flask calls it the "application factory pattern"). FastAPI supports it via
Uvicorn's --factory flag.

Architecture:
  API routes ONLY:
    1. Authenticate the caller
    2. Validate input (Pydantic handles this)
    3. Call an application use case
    4. Serialize the result

  Routes must NOT contain:
    - Raw SQL or DDL
    - Policy decisions
    - Background task scheduling
    - Direct database session management (use dependencies)
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ephemeralshield import __version__
from ephemeralshield.api.routes.health import create_health_router
from ephemeralshield.bootstrap import create_engine, create_session_factory
from ephemeralshield.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manage application startup and shutdown lifecycle.

    WHY lifespan instead of @app.on_event("startup")?
      on_event is deprecated in FastAPI. The lifespan context manager is the
      recommended replacement. It ensures cleanup runs even if the app crashes.

    What happens here:
      1. STARTUP: Create the database engine and session factory.
         Store them in app.state so dependencies can access them.
      2. YIELD: App runs and serves requests.
      3. SHUTDOWN: Dispose the engine (close all pooled connections).
         This prevents connection leaks when the container stops.
    """
    settings = get_settings()

    # Create database engine and session factory
    engine: AsyncEngine = create_engine(settings)
    session_factory: async_sessionmaker[AsyncSession] = create_session_factory(engine)

    # Store in app.state — accessible from request dependencies
    # WHY app.state? It's FastAPI's official mechanism for sharing resources
    # across requests without using global variables.
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.settings = settings

    yield  # App runs here

    # Cleanup: close all database connections in the pool
    await engine.dispose()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns a fully configured FastAPI instance with:
      - Health check routes (Phase 1)
      - CORS disabled (mTLS proxy handles this in production)
      - No auto-generated docs in production (security)
      - Version in response headers
    """
    settings = get_settings()

    # ---------------------------------------------------------------------------
    # Determine whether to expose API documentation
    # ---------------------------------------------------------------------------
    # In production, API docs should be behind authentication (§3.3).
    # In development, they're invaluable for testing.
    # ---------------------------------------------------------------------------
    docs_url: str | None = "/docs" if settings.environment == "development" else None
    redoc_url: str | None = "/redoc" if settings.environment == "development" else None

    app = FastAPI(
        title="EphemeralShield",
        description=(
            "PostgreSQL just-in-time credential broker. "
            "Provisions short-lived, read-only database credentials "
            "with automatic revocation and tamper-evident audit."
        ),
        version=__version__,
        docs_url=docs_url,
        redoc_url=redoc_url,
        lifespan=lifespan,
        # ---------------------------------------------------------------------------
        # OpenAPI configuration
        # ---------------------------------------------------------------------------
        # Servers list helps generated clients use the correct base URL.
        # In development, this points to localhost.
        # In production, the mTLS proxy URL would be here.
        # ---------------------------------------------------------------------------
        servers=[
            {"url": f"http://localhost:{settings.app_port}", "description": "Development"},
        ],
    )

    # ---------------------------------------------------------------------------
    # Middleware
    # ---------------------------------------------------------------------------
    # CORS is restrictive by default. In production, the Nginx mTLS proxy
    # handles CORS. We only allow localhost origins in development for tools
    # like Swagger UI.
    # ---------------------------------------------------------------------------
    if settings.environment == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:8000"],
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

    # ---------------------------------------------------------------------------
    # Register route modules
    # ---------------------------------------------------------------------------
    # Each route module is a separate router. This keeps the main app.py clean
    # and makes it easy to add/remove feature routes per phase.
    # ---------------------------------------------------------------------------
    app.include_router(
        create_health_router(),
        tags=["Health"],
    )

    return app


def create_app_for_type_checking() -> FastAPI:
    """
    Type-stub helper for mypy.

    This function exists solely so mypy can verify the create_app return type
    without needing to resolve all runtime dependencies. It should never be
    called at runtime.
    """
    return create_app()  # pragma: no cover
