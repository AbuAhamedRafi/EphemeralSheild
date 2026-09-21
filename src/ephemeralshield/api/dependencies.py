"""
EphemeralShield — FastAPI Dependencies.

Dependencies are FastAPI's dependency injection system. They provide shared
resources (database sessions, settings, authenticated users) to route handlers
without the handlers needing to know HOW those resources are created.

WHY dependency injection?
  1. Testability — tests inject mock sessions/settings without patching globals
  2. Lifecycle — sessions are automatically closed after each request
  3. Separation — routes don't know about SQLAlchemy, just the session interface
  4. Consistency — every route gets the same setup/teardown behavior

Example usage in a route:
    @router.get("/example")
    async def example(
        db: AsyncSession = Depends(get_db_session),
        settings: Settings = Depends(get_current_settings),
    ):
        ...
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ephemeralshield.settings import Settings


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a database session from the application's session factory.

    This is a FastAPI dependency that:
      1. Gets the session factory from app.state (created in lifespan)
      2. Creates a new session for this request
      3. Yields it to the route handler
      4. Closes it when the request completes (even on exceptions)

    WHY 'yield' instead of 'return'?
      The yield pattern creates a context manager. FastAPI calls __anext__()
      to get the session, and __anext__() again after the route finishes to
      run cleanup. This guarantees the session is closed and the database
      connection is returned to the pool.

    WHY get the factory from request.app.state?
      This avoids global variables. Each test can create a fresh app with a
      test-specific database, and the dependency automatically uses it.
    """
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_current_settings(request: Request) -> Settings:
    """
    Return the application settings from app.state.

    WHY a dependency instead of calling get_settings() directly?
      In tests, you can override this dependency with test settings.
      This is cleaner than monkeypatching the lru_cache.
    """
    settings: Settings = request.app.state.settings
    return settings


# ---------------------------------------------------------------------------
# Type aliases for cleaner route signatures
# ---------------------------------------------------------------------------
# Instead of: db: AsyncSession = Depends(get_db_session)
# Write:      db: DbSession
#
# This is a FastAPI convention using PEP 593 Annotated types.
# ---------------------------------------------------------------------------
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentSettings = Annotated[Settings, Depends(get_current_settings)]
