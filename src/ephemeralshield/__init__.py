"""
EphemeralShield — PostgreSQL Just-in-Time Credential Broker.

This is the top-level package marker. It defines the project version as the
single source of truth (referenced by pyproject.toml and API responses).

WHY define __version__ here?
  - The API can include it in response headers for debugging.
  - The CLI can show it in `shieldctl --version`.
  - It avoids hardcoding version strings in multiple places.
"""

__version__ = "0.1.0"
