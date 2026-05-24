"""`cairn dev` — development & test-harness helpers.

These commands are intended for the multi-user/multi-cairn test
methodology (``tests/agent_smoke/multi-user-multi-cairn/``) and for
local development. They are not part of the operator-facing cairn
workflow.
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..dev.server_lifecycle import serve as _serve_impl

app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Development & test-harness helpers — spin up HTTP MCP servers "
        "and fixture cairns for the multi-user/multi-cairn methodology. "
        "Not for production cairn use."
    ),
)


@app.command(name="serve")
def serve(
    cairn_path: Path | None = typer.Option(
        None,
        "--cairn-path",
        help=(
            "Path to a cairn directory the server should serve "
            "(passed through to `cairn mcp`)."
        ),
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int | None = typer.Option(
        None,
        "--port",
        help="Port to bind. Default: pick a free one with bind-port-0.",
    ),
    path: str = typer.Option("/mcp", "--path"),
) -> None:
    """Start an HTTP MCP server in the background and print its connection info."""
    info = _serve_impl(cairn_path=cairn_path, host=host, port=port, path=path)
    typer.echo(
        f"started pid={info.pid} port={info.port} url={info.url} log={info.log_path}"
    )


@app.command(name="stop")
def stop() -> None:
    """Stop one or all dev MCP servers. (Not yet implemented.)"""
    raise typer.Exit(code=2)


@app.command(name="scaffold-fixture")
def scaffold_fixture() -> None:
    """Scaffold a fixture project + cairn. (Not yet implemented.)"""
    raise typer.Exit(code=2)
