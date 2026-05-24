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
from ..dev.server_lifecycle import stop as _stop_impl

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
def stop(
    pid: int | None = typer.Option(None, "--pid", help="Stop only this PID."),
    all_: bool = typer.Option(
        False, "--all", help="Stop every recorded dev server."
    ),
) -> None:
    """Stop one or all dev MCP servers."""
    if (pid is None) == (not all_):
        typer.echo("error: pass exactly one of --pid or --all.", err=True)
        raise typer.Exit(code=2)
    stopped = _stop_impl(pid=pid, all_=all_)
    if not stopped:
        typer.echo("no dev servers to stop.")
        return
    typer.echo(f"stopped pids: {', '.join(str(p) for p in stopped)}")


@app.command(name="scaffold-fixture")
def scaffold_fixture() -> None:
    """Scaffold a fixture project + cairn. (Not yet implemented.)"""
    raise typer.Exit(code=2)
