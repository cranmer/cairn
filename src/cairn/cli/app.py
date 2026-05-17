"""Top-level Typer app — entry point for the ``cairn`` console script."""

from __future__ import annotations

import typer

from .collaborator_cmd import app as collaborator_app
from .decision_cmd import app as decision_app
from .init_cmd import init
from .status_cmd import status
from .validate_cmd import validate

app = typer.Typer(
    no_args_is_help=True,
    help="Cairn — manage a cairn (research project repository).",
    add_completion=False,
)

app.command(name="init")(init)
app.add_typer(collaborator_app, name="collaborator")
app.add_typer(decision_app, name="decision")
app.command(name="validate")(validate)
app.command(name="status")(status)


@app.command(name="version")
def _version() -> None:
    """Print the Cairn package version."""
    from .. import __version__

    typer.echo(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
