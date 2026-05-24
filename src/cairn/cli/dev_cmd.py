"""`cairn dev` — development & test-harness helpers.

These commands are intended for the multi-user/multi-cairn test
methodology (``tests/agent_smoke/multi-user-multi-cairn/``) and for
local development. They are not part of the operator-facing cairn
workflow.
"""

from __future__ import annotations

import typer

app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Development & test-harness helpers — spin up HTTP MCP servers "
        "and fixture cairns for the multi-user/multi-cairn methodology. "
        "Not for production cairn use."
    ),
)


@app.command(name="serve")
def serve() -> None:
    """Start an HTTP MCP server in the background. (Not yet implemented.)"""
    raise typer.Exit(code=2)


@app.command(name="stop")
def stop() -> None:
    """Stop one or all dev MCP servers. (Not yet implemented.)"""
    raise typer.Exit(code=2)


@app.command(name="scaffold-fixture")
def scaffold_fixture() -> None:
    """Scaffold a fixture project + cairn. (Not yet implemented.)"""
    raise typer.Exit(code=2)
