"""
EphemeralShield — Admin CLI (shield-admin).

The operator CLI for managing resources, policies, principals, and audit.

Entry point: shield-admin (defined in pyproject.toml [project.scripts])
"""

import typer

app = typer.Typer(
    name="shield-admin",
    help="EphemeralShield Admin — Manage resources, policies, and audit.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Show the EphemeralShield version."""
    from ephemeralshield import __version__

    typer.echo(f"EphemeralShield Admin v{__version__}")
