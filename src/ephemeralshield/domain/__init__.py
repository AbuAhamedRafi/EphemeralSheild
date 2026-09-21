"""
EphemeralShield — Domain Layer.

This package contains the core business logic: entities, value objects,
state machines, policies, errors, and port interfaces.

CRITICAL RULE (§1.4): This package has ZERO framework imports.
  - No SQLAlchemy
  - No FastAPI
  - No Redis
  - No Psycopg

The domain layer is pure Python. It can be tested without any infrastructure.
This is enforced by import-linter in CI (see pyproject.toml).
"""
