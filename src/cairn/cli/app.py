"""Top-level Typer app — entry point for the ``cairn`` console script."""

from __future__ import annotations

import typer

from .action_cmd import app as action_app
from .collaborator_cmd import app as collaborator_app
from .decision_cmd import app as decision_app
from .exploration_cmd import app as exploration_app
from .finding_cmd import app as finding_app
from .init_cmd import init
from .link_cmd import link
from .mcp_cmd import mcp
from .register_cmd import register, registered, unregister
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
app.add_typer(action_app, name="action")
app.add_typer(exploration_app, name="exploration")
app.add_typer(finding_app, name="finding")
app.command(name="validate")(validate)
app.command(name="status")(status)
app.command(name="link")(link)
app.command(name="register")(register)
app.command(name="unregister")(unregister)
app.command(name="registered")(registered)
app.command(name="mcp")(mcp)


@app.command(name="version")
def _version() -> None:
    """Print the Cairn package version."""
    from .. import __version__

    typer.echo(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
