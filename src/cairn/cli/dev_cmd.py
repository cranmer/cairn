"""`cairn dev` — development & test-harness helpers.

These commands are intended for the multi-user/multi-cairn test
methodology (``tests/agent_smoke/multi-user-multi-cairn/``) and for
local development. They are not part of the operator-facing cairn
workflow.
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..dev.fixtures import scaffold_fixture as _scaffold_impl
from ..dev.fixtures_data import FIXTURES
from ..dev.server_lifecycle import list_servers as _list_impl
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


@app.command(name="list")
def list_() -> None:
    """List running dev MCP servers."""
    servers = _list_impl()
    if not servers:
        typer.echo("no dev servers running.")
        return
    for s in servers:
        typer.echo(
            f"pid={s.pid} port={s.port} url={s.url} cairn={s.cairn_path or '-'}"
        )


@app.command(name="scaffold-fixture")
def scaffold_fixture(
    name: str = typer.Argument(
        ...,
        help=f"Fixture to scaffold. Known: {', '.join(sorted(FIXTURES))}.",
    ),
    dest: Path = typer.Option(
        ...,
        "--dest",
        help="Destination dir; receives projects/<name>/ and cairns/<name>/.",
        file_okay=False,
        dir_okay=True,
    ),
    http_endpoint: str | None = typer.Option(
        None,
        "--http-endpoint",
        help="Required for HTTP-paired fixtures (e.g. shared-physics-paper).",
    ),
) -> None:
    """Scaffold a fixture project + paired cairn under --dest."""
    if name not in FIXTURES:
        typer.echo(
            f"error: unknown fixture {name!r}. "
            f"Known: {', '.join(sorted(FIXTURES))}.",
            err=True,
        )
        raise typer.Exit(code=2)
    fix = FIXTURES[name]
    if fix.paired_via_http and not http_endpoint:
        typer.echo(
            f"error: fixture {name!r} requires --http-endpoint "
            "(e.g. http://127.0.0.1:8765).",
            err=True,
        )
        raise typer.Exit(code=2)
    try:
        project_dir, cairn_dir = _scaffold_impl(
            name, dest, http_endpoint=http_endpoint
        )
    except Exception as exc:
        typer.echo(f"error: scaffold failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"project={project_dir}")
    typer.echo(f"cairn={cairn_dir}")
