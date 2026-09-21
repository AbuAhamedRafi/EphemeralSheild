"""
EphemeralShield — Admin CLI main entry point (shield-admin).

This module is the Typer app instance referenced by pyproject.toml.
"""

from ephemeralshield.admin import app

__all__ = ["app"]
