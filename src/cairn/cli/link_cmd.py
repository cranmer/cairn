"""`cairn link [<project-repo>]` — pair a project repo with a cairn.

Writes a ``cairn.toml`` at the project repo root so agents working inside
the project repo can discover the paired cairn via cwd-walk. See ADR-0006
and ADR-0010.

Three modes:
- ``--endpoint <url> --name <handle>`` (US-P-12): writes a remote-mode pointer to an
  HTTP MCP server.  Pairing travels with the repo; credentials do not.
- ``--name <cairn-name>`` (preferred local): looks up the cairn in the user's
  MCP registry. Run from anywhere — typically inside the project repo.
- No ``--name``, no ``--endpoint`` (path-based fallback): resolves the cairn from
  cwd-walk.  Run from inside the cairn directory.
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..cairn_toml import POINTER_FILE, CairnTomlError, write_pointer
from ..paths import is_cairn_root, resolve_cairn
from ..registry import lookup
from ._common import resolve_or_exit


def link(
    project_repo: Path = typer.Argument(
        None,
        help=(
            "Path to the project repo to pair with the cairn. "
            "Defaults to the current working directory."
        ),
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help=(
            "For local mode: the registry handle you chose when running "
            "`cairn register <handle> <path>` (looks up in the MCP registry). "
            "For remote mode (with --endpoint): the cairn handle on the remote "
            "server (the value passed as the `cairn` MCP parameter)."
        ),
    ),
    endpoint: str | None = typer.Option(
        None,
        "--endpoint",
        help=(
            "Remote MCP server URL (e.g. https://cairn.example.com). "
            "Requires --name (the cairn handle on that server). "
            "Writes a remote-mode cairn.toml; credentials are NOT stored here "
            "— use CAIRN_BEARER_TOKEN or ~/.config/cairn/credentials.toml."
        ),
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing cairn.toml at the project repo root.",
    ),
    no_probe: bool = typer.Option(
        False,
        "--no-probe",
        help=(
            "Skip the connectivity check when writing a remote-mode pointer. "
            "Useful for offline pairing or environments where the server is not "
            "yet reachable from this machine."
        ),
    ),
) -> None:
    """Pair a project repo with a cairn by writing a cairn.toml pointer."""
    project = (project_repo or Path.cwd()).resolve()
    if not project.is_dir():
        typer.echo(f"error: project-repo path is not a directory: {project}", err=True)
        raise typer.Exit(code=1)
    target = project / POINTER_FILE
    if target.exists() and not force:
        typer.echo(
            f"error: {target} already exists. Pass --force to overwrite.", err=True
        )
        raise typer.Exit(code=1)

    # --- Remote MCP mode (--endpoint + --name) --------------------------------
    if endpoint is not None:
        if name is None:
            typer.echo(
                "error: --endpoint requires --name (the cairn handle on the remote server).",
                err=True,
            )
            raise typer.Exit(code=1)

        if not no_probe:
            _probe_endpoint(endpoint)

        try:
            written = write_pointer(project, endpoint=endpoint, name=name)
        except CairnTomlError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from None

        typer.echo(f"Linked {project} → remote cairn '{name}' at {endpoint}.")
        typer.echo(f"Wrote {written}.")
        typer.echo(
            "\nPairing info (share with collaborators who need to reach this cairn):\n"
            f"  endpoint: {endpoint}\n"
            f"  cairn:    {name}\n"
            "\nCredentials (do NOT commit):\n"
            "  Set CAIRN_BEARER_TOKEN=<token> in your environment, or add:\n"
            f'    [endpoints]\n    "{endpoint}" = "<token>"\n'
            "  to ~/.config/cairn/credentials.toml (chmod 600).\n"
            "\nFor Claude Code agents, register the MCP server:\n"
            f"  claude mcp add cairn-remote --transport http --url {endpoint.rstrip('/')}/mcp\n"
            "Then restart any open Claude Code sessions."
        )
        return

    # --- Local registry mode (--name only) ------------------------------------
    if name is not None:
        existing = lookup(name)
        if existing is None:
            typer.echo(
                f"error: '{name}' is not registered. Add it first with "
                f"`cairn register {name} <path-to-cairn>`, then re-run link. "
                f"Listed registry: `cairn registered`.",
                err=True,
            )
            raise typer.Exit(code=1)
        try:
            written = write_pointer(project, name=name)
        except CairnTomlError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from None
        typer.echo(
            f"Linked {project} → cairn '{name}' (at {existing.path}). "
            f"Wrote {written}."
        )
        typer.echo(
            "\nFor agents in Claude Code sessions opened here to reach the "
            "cairn, the cairn MCP server must be registered with Claude Code "
            "(one-time, ever):\n"
            "  claude mcp add cairn cairn mcp\n"
            "Then restart any open Claude Code sessions to pick it up."
        )
        return

    # --- Local path-based fallback (no --name, no --endpoint) -----------------
    try:
        cairn_paths = resolve_or_exit()
    except SystemExit:
        # resolve_or_exit already echoed the error; add guidance and re-exit.
        typer.echo(
            "hint: pass --name <registered-cairn> to link without being inside "
            "the cairn directory. See `cairn registered`.\n"
            "hint: pass --endpoint <url> --name <handle> to link to a remote MCP server.",
            err=True,
        )
        raise typer.Exit(code=2) from None

    if project == cairn_paths.root.resolve():
        typer.echo(
            f"error: refusing to link a cairn ({cairn_paths.root}) to itself. "
            f"Did you mean to pass a separate project-repo path?",
            err=True,
        )
        raise typer.Exit(code=1)

    if not is_cairn_root(cairn_paths.root):
        typer.echo(f"error: {cairn_paths.root} is not a cairn root", err=True)
        raise typer.Exit(code=1)
    try:
        written = write_pointer(project, path=cairn_paths.root)
    except CairnTomlError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"Linked {project} → {cairn_paths.root}. Wrote {written}.")
    typer.echo(
        "\nFor agents in Claude Code sessions opened here to reach the "
        "cairn, the cairn MCP server must be registered with Claude Code "
        "(one-time, ever):\n"
        "  claude mcp add cairn cairn mcp\n"
        "Then restart any open Claude Code sessions to pick it up."
    )


def _probe_endpoint(endpoint: str) -> None:
    """Check that the endpoint is reachable. Fails fast with a clear error."""
    import urllib.error
    import urllib.request

    probe_url = endpoint.rstrip("/")
    # A GET to the root should either succeed or return a recognisable HTTP error.
    # A connection error (name not resolved, refused, etc.) is the failure mode
    # we care about.
    try:
        req = urllib.request.Request(probe_url, method="GET")
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError:
        # Any HTTP response means the server is reachable, even if it returned
        # a 4xx/5xx for the root path.
        return
    except urllib.error.URLError as exc:
        typer.echo(
            f"error: could not reach {endpoint}: {exc.reason}\n"
            "Pass --no-probe to skip this check and write the pointer anyway.",
            err=True,
        )
        raise typer.Exit(code=1) from None
    except Exception as exc:
        typer.echo(
            f"error: connectivity check failed for {endpoint}: {exc}\n"
            "Pass --no-probe to skip this check and write the pointer anyway.",
            err=True,
        )
        raise typer.Exit(code=1) from None


# Silence unused-import linting (resolve_cairn imported for potential future use).
_ = resolve_cairn
