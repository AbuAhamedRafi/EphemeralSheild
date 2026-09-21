"""
EphemeralShield — SQLAlchemy ORM Base.

This module defines the declarative base class that all ORM models inherit from.
It also configures common conventions for table naming, constraints, and indexes.

WHY a separate module for the base?
  Alembic's env.py needs to import Base.metadata to detect models for
  auto-generation. If Base lived in a module that imports heavy dependencies,
  Alembic would need to initialize the entire application just to read metadata.
  Keeping Base isolated prevents that circular dependency.

WHY DeclarativeBase (SQLAlchemy 2.0 style)?
  SQLAlchemy 2.0 introduced a new declarative base using native Python classes
  instead of the old declarative_base() factory function. Benefits:
    - Full type checking support (mypy knows about column types)
    - No global registry side effects
    - Cleaner syntax with Mapped[] and mapped_column()

Phase 1: Only the base class. ORM models are added in Phase 2.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all EphemeralShield ORM models.

    All models inherit from this class, which provides:
      - Automatic table name generation (can be overridden)
      - Shared metadata object (used by Alembic for migration generation)
      - Common type mapping configuration

    Example usage (Phase 2):
        class CredentialLease(Base):
            __tablename__ = "credential_leases"
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
            ...
    """

    pass
