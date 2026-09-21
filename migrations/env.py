"""
EphemeralShield — Alembic Migration Environment.

This file configures how Alembic runs migrations against the control-plane
database (broker-db).

KEY DESIGN DECISIONS:

1. ASYNC ENGINE: We use run_async_migrations() because our application uses
   async SQLAlchemy with Psycopg 3. Alembic itself is synchronous, so we
   bridge between the two using asyncio.run() and async engine methods.

2. URL FROM SETTINGS: The database URL comes from settings.py, not from
   alembic.ini. This ensures migrations use the same configuration as the
   application (same env vars, same .env file).

3. TARGET METADATA: We import Base.metadata from engine.py so Alembic knows
   about our ORM models. When you run `alembic revision --autogenerate`,
   Alembic compares the models to the database and generates migration code.

4. NO create_all(): The development plan (§1.4) explicitly prohibits using
   SQLAlchemy's create_all() in production. All schema changes go through
   versioned, reviewable Alembic migrations.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from ephemeralshield.infrastructure.database.engine import Base
from ephemeralshield.settings import get_settings

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Set up Python logging from alembic.ini's [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the metadata Alembic uses to detect model changes
# When you add a new ORM model, it must inherit from Base for Alembic to see it
target_metadata = Base.metadata

# Override the database URL from alembic.ini with the one from settings
# This ensures we use the same URL as the running application
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.broker_db_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This generates SQL scripts without actually connecting to the database.
    Useful for reviewing what changes will be made before running them.

    Usage: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations using a synchronous database connection.

    This is called from within run_async_migrations() after the async
    engine creates a sync connection via run_sync().
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations using an async engine.

    WHY this pattern?
      Alembic's migration runner is synchronous, but our database driver
      (psycopg 3) is async. We create an async engine, get a sync connection
      wrapper via conn.run_sync(), and pass it to Alembic's synchronous
      migration runner.

      This is the official pattern recommended by SQLAlchemy for async:
      https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No connection pooling for migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (connected to the database).

    This is the normal path — Alembic connects to the database and applies
    migrations directly.
    """
    asyncio.run(run_async_migrations())


# Determine which mode to run in
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
