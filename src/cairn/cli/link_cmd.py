"""`cairn link [<project-repo>]` — pair a project repo with a cairn.

Writes a ``cairn.toml`` at the project repo root so agents working inside
the project repo can discover the paired cairn via cwd-walk. See ADR-0006
and ADR-0010.

Two modes:
- ``--name <cairn-name>`` (preferred): looks up the cairn in the user's
  MCP registry. Run from anywhere — typically inside the project repo.
- No ``--name`` (path-based fallback): resolves the cairn from cwd-walk.
  Run from inside the cairn directory.
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
            "The handle you chose for this cairn when running "
            "`cairn register <handle> <path>` (not the cairn's directory "
            "name — the registry handle, which is whatever short name "
            "you picked). Looking it up in the MCP registry; works from "
            "anywhere. If omitted, the cairn is linked by relative path "
            "and the command must be run from inside the cairn directory."
        ),
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing cairn.toml at the project repo root.",
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

    # No --name: link by relative path. Requires cwd-walk to find the cairn.
    # If the project_repo argument was given and IS a cairn, treat that as the
    # cairn-side argument and require an explicit --name — refusing because the
    # user likely got the argument order wrong.
    try:
        cairn_paths = resolve_or_exit()
    except SystemExit:
        # resolve_or_exit already echoed the error; add guidance and re-exit.
        typer.echo(
            "hint: pass --name <registered-cairn> to link without being inside "
            "the cairn directory. See `cairn registered`.",
            err=True,
        )
        raise typer.Exit(code=2) from None

    # If the user is linking from inside the same directory they're trying to
    # link, surface that.
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


# Silence unused-import linting (resolve_cairn imported for potential future use).
_ = resolve_cairn
