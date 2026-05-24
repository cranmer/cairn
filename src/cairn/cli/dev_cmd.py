"""`cairn dev` — development & test-harness helpers.

These commands are intended for the multi-user/multi-cairn test
methodology (``tests/agent_smoke/multi-user-multi-cairn/``) and for
local development. They are not part of the operator-facing cairn
workflow.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer

from ..dev.fixtures import scaffold_fixture as _scaffold_impl
from ..dev.fixtures_data import FIXTURES
from ..dev.server_lifecycle import list_servers as _list_impl
from ..dev.server_lifecycle import serve as _serve_impl
from ..dev.server_lifecycle import stop as _stop_impl

_REMOTE_ENV_VAR = "CAIRN_DEV_REMOTE_URL"


def _resolve_remote(remote_flag: str | None) -> str | None:
    """Return *remote_flag* if set; otherwise fall back to CAIRN_DEV_REMOTE_URL.

    Empty-string env var counts as unset.
    """
    if remote_flag:
        return remote_flag
    env_val = os.environ.get(_REMOTE_ENV_VAR)
    return env_val or None

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
        help=("Path to a cairn directory the server should serve (passed through to `cairn mcp`)."),
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
    typer.echo(f"started pid={info.pid} port={info.port} url={info.url} log={info.log_path}")


@app.command(name="stop")
def stop(
    pid: int | None = typer.Option(None, "--pid", help="Stop only this PID."),
    all_: bool = typer.Option(False, "--all", help="Stop every recorded dev server."),
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
        typer.echo(f"pid={s.pid} port={s.port} url={s.url} cairn={s.cairn_path or '-'}")


def _summarize_local_catalog() -> dict[str, dict]:
    return {
        name: {
            "collaborators": [c.id for c in fix.collaborators],
            "decisions": len(fix.decisions),
            "questions": len(fix.questions),
            "findings": len(fix.findings),
        }
        for name, fix in FIXTURES.items()
    }


def _fmt_summary(s: dict) -> str:
    return (
        f"c={len(s.get('collaborators') or [])} "
        f"d={s.get('decisions', 0)} "
        f"q={s.get('questions', 0)} "
        f"f={s.get('findings', 0)}"
    )


@app.command(name="fixtures")
def fixtures(
    remote: str | None = typer.Option(
        None,
        "--remote",
        help=(
            "Compare the local fixture catalog against a remote dev MCP "
            "server at this URL. Defaults to the CAIRN_DEV_REMOTE_URL env "
            "var if set (source .env for the project's dev server). "
            "Without either, prints the local catalog."
        ),
    ),
) -> None:
    """List the fixture catalog; with --remote, compare against a server.

    Useful before running `cairn dev scaffold-fixture --remote` to check
    that the client and server agree on fixture contents (see ADR-0013).
    """
    local = _summarize_local_catalog()
    remote = _resolve_remote(remote)

    if not remote:
        for name in sorted(local):
            typer.echo(f"{name:<24} {_fmt_summary(local[name])}")
        return

    from ..credentials import missing_token_hint, resolve_token
    from ..mcp.remote import (
        RemoteAuthError,
        RemoteCallError,
        RemoteNetworkError,
        call_tool,
    )

    token = resolve_token(remote)
    if token is None:
        typer.echo(f"error: {missing_token_hint(remote)}", err=True)
        raise typer.Exit(code=1)
    try:
        result = call_tool(remote, "list_fixtures", {}, token=token)
    except (RemoteAuthError, RemoteNetworkError, RemoteCallError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    remote_entries = result.get("fixtures") or []
    remote_catalog: dict[str, dict] = {entry["name"]: entry["summary"] for entry in remote_entries}

    all_names = sorted(set(local) | set(remote_catalog))
    any_drift = False
    typer.echo(f"{'fixture':<24} {'local':<22} {'remote':<22} status")
    for name in all_names:
        loc = local.get(name)
        rem = remote_catalog.get(name)
        if loc is None:
            status = "client-missing"
            any_drift = True
            local_col = "(absent)"
            remote_col = _fmt_summary(rem) if rem else "(absent)"
        elif rem is None:
            status = "remote-missing"
            any_drift = True
            local_col = _fmt_summary(loc)
            remote_col = "(absent)"
        elif loc == rem:
            status = "match"
            local_col = _fmt_summary(loc)
            remote_col = _fmt_summary(rem)
        else:
            status = "drift"
            any_drift = True
            local_col = _fmt_summary(loc)
            remote_col = _fmt_summary(rem)
        typer.echo(f"{name:<24} {local_col:<22} {remote_col:<22} {status}")

    if any_drift:
        raise typer.Exit(code=1)


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
        help=(
            "Write an HTTP-paired cairn.toml pointing at this URL. The cairn "
            "is still scaffolded locally — use --remote instead for a "
            "server-side cairn."
        ),
    ),
    remote: str | None = typer.Option(
        None,
        "--remote",
        help=(
            "Truly-remote mode: ask the dev MCP server at <URL> to scaffold "
            "the cairn server-side, and only materialize the project repo "
            "locally. Defaults to the CAIRN_DEV_REMOTE_URL env var if set. "
            "Mutually exclusive with --http-endpoint."
        ),
    ),
    as_name: str | None = typer.Option(
        None,
        "--as",
        help=(
            "Remote-mode only: register the fixture under this cairn handle "
            "on the server instead of the fixture's default name."
        ),
    ),
) -> None:
    """Scaffold a fixture project + paired cairn under --dest."""
    remote = _resolve_remote(remote)
    if name not in FIXTURES:
        typer.echo(
            f"error: unknown fixture {name!r}. Known: {', '.join(sorted(FIXTURES))}.",
            err=True,
        )
        raise typer.Exit(code=2)
    if remote and http_endpoint:
        typer.echo(
            "error: --remote and --http-endpoint are mutually exclusive.",
            err=True,
        )
        raise typer.Exit(code=2)
    if as_name and not remote:
        typer.echo(
            "error: --as is only valid with --remote.",
            err=True,
        )
        raise typer.Exit(code=2)

    if remote:
        from ..credentials import missing_token_hint, resolve_token
        from ..dev.fixtures import scaffold_project
        from ..mcp.remote import (
            RemoteAuthError,
            RemoteCallError,
            RemoteNetworkError,
            call_tool,
        )

        token = resolve_token(remote)
        if token is None:
            typer.echo(f"error: {missing_token_hint(remote)}", err=True)
            raise typer.Exit(code=1)
        try:
            result = call_tool(
                remote,
                "scaffold_fixture",
                {"name": name, "as_name": as_name} if as_name else {"name": name},
                token=token,
            )
        except RemoteAuthError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from None
        except RemoteNetworkError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from None
        except RemoteCallError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from None

        resolved_name = result.get("cairn")
        summary = result.get("summary") or {}
        if not resolved_name:
            typer.echo(
                f"error: remote did not return a cairn handle (got {result!r}).",
                err=True,
            )
            raise typer.Exit(code=1)
        # Verify against the local fixture catalog so client/server drift
        # surfaces before we materialize anything.
        from ..dev.fixtures_data import FIXTURES as _LOCAL_FIXTURES

        local_fix = _LOCAL_FIXTURES[name]
        local_summary = {
            "collaborators": [c.id for c in local_fix.collaborators],
            "decisions": len(local_fix.decisions),
            "questions": len(local_fix.questions),
            "findings": len(local_fix.findings),
        }
        for key, expected in local_summary.items():
            got = summary.get(key)
            if got != expected:
                typer.echo(
                    f"error: fixture catalog drift between client and remote "
                    f"on field {key!r}: local={expected!r}, remote={got!r}. "
                    "Bump the cairn package on the older side.",
                    err=True,
                )
                raise typer.Exit(code=1)

        project_dir = dest / "projects" / name
        scaffold_project(name, project_dir, http_endpoint=remote, cairn_name=resolved_name)
        typer.echo(f"project={project_dir}")
        typer.echo(f"remote_cairn={resolved_name} at {remote}")
        return

    try:
        project_dir, cairn_dir = _scaffold_impl(name, dest, http_endpoint=http_endpoint)
    except Exception as exc:
        typer.echo(f"error: scaffold failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"project={project_dir}")
    typer.echo(f"cairn={cairn_dir}")
