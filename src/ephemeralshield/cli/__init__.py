"""
EphemeralShield — CLI (shieldctl).

The end-user CLI for requesting database access, connecting to targets,
listing leases, and revoking credentials.

Entry point: shieldctl (defined in pyproject.toml [project.scripts])

Built with Typer, which provides:
  - Automatic help generation
  - Type-safe argument parsing
  - Shell completion
  - Rich terminal output
"""

import typer

app = typer.Typer(
    name="shieldctl",
    help="EphemeralShield — Request and manage just-in-time database credentials.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Show the EphemeralShield version."""
    from ephemeralshield import __version__

    typer.echo(f"EphemeralShield v{__version__}")
