"""
EphemeralShield — Composition Root (Bootstrap).

This module is the ONLY place where concrete implementations are wired to
abstract interfaces (ports). It's the "dependency injection container" of
the application.

WHY a composition root?
  The development plan (§1.4) enforces strict dependency direction:
    domain → (nothing)
    application → domain + typed ports
    infrastructure → implements ports
    api/worker/cli → application use cases

  Only the composition root wires implementations to ports. This means:
    - Domain code never imports SQLAlchemy or FastAPI
    - Application code depends on abstract interfaces, not concrete databases
    - You can swap PostgreSQL for a test double without touching business logic

  In Phase 1, this module only creates the database engine.
  As phases progress, it will wire repositories, adapters, and use cases.

Usage:
    from ephemeralshield.bootstrap import create_engine, create_session_factory

    engine = create_engine(settings)
    async_session = create_session_factory(engine)
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ephemeralshield.settings import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine for the control-plane database.

    WHY async?
      FastAPI is async-first. Using sync database calls would block the event
      loop, limiting concurrency to 1 request at a time per worker.
      Async allows hundreds of concurrent requests with a small thread pool.

    WHY psycopg (v3)?
      Psycopg 3 has native async support (not a wrapper around sync like
      psycopg2 + asyncpg). It also supports SCRAM authentication and
      SQL composition for safe identifier handling — both critical for
      the target adapter in Phase 2.

    Pool configuration:
      - pool_size=5: Keep 5 connections warm in the pool
      - max_overflow=10: Allow up to 15 total under burst load
      - pool_pre_ping=True: Test connections before use (handles DB restarts)
      - pool_recycle=300: Recycle connections every 5 min (prevents stale state)
    """
    return create_async_engine(
        settings.broker_db_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=(settings.environment == "development"),
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Create a session factory bound to the given engine.

    WHY a factory instead of a global session?
      The plan (§1.4) requires: "Use one unit of work per control-plane
      operation. Do not share async sessions between concurrent tasks."

      A session factory creates a NEW session for each request/operation.
      Sharing sessions between concurrent async tasks causes race conditions
      and transaction isolation violations.

    WHY expire_on_commit=False?
      After committing a transaction, SQLAlchemy normally "expires" all loaded
      attributes, forcing a new query on next access. With async, this causes
      "greenlet_spawn has not been called" errors because the lazy load happens
      outside the async context. Setting expire_on_commit=False avoids this —
      you explicitly refresh objects when you need fresh data.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a database session and ensure it's closed after use.

    This is designed to be used as a FastAPI dependency:

        @app.get("/example")
        async def example(db: AsyncSession = Depends(get_db_session)):
            ...

    The 'yield' pattern ensures the session is closed even if the request
    handler raises an exception. This prevents connection leaks.
    """
    async with session_factory() as session:
        yield session
