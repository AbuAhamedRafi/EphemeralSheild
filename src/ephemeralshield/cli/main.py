"""
EphemeralShield — CLI main entry point (shieldctl).

This module is the Typer app instance referenced by pyproject.toml.
"""

from ephemeralshield.cli import app

__all__ = ["app"]
