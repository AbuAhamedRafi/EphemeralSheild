"""Phase 1 - Initial migration (connectivity verification).

Revision ID: 001
Revises: None
Create Date: 2026-09-21

This migration verifies that Alembic can connect to the broker-db and execute
DDL. It creates no tables — those are added in Phase 2.

WHY an empty migration?
  1. Validates the Alembic → SQLAlchemy → Psycopg 3 → PostgreSQL 17 pipeline
  2. Creates the alembic_version table (Alembic's migration tracking)
  3. Proves 'make migrate' works from day one
  4. Establishes the revision chain that Phase 2 migrations depend on

This is a standard practice: the first migration in any project is a
"hello world" that proves the infrastructure works before adding business logic.
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 1: No schema changes. Connectivity verification only."""
    # Phase 2 will add: principals, credential_leases, audit_ledger, etc.
    pass


def downgrade() -> None:
    """Reverse Phase 1: Nothing to reverse."""
    pass
