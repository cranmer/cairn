"""`cairn link <project-repo>` — pair a project repo with a cairn.

Writes a ``cairn.toml`` at the project repo root so agents working inside
the project repo can discover the paired cairn via cwd-walk. See ADR-0006
and ADR-0010.
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..cairn_toml import POINTER_FILE, CairnTomlError, write_pointer
from ..paths import is_cairn_root
from ..registry import lookup
from ._common import resolve_or_exit


def link(
    project_repo: Path = typer.Argument(
        ...,
        help=(
            "Path to the project repo to pair with the cairn. "
            "A `cairn.toml` will be written at its root."
        ),
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help=(
            "Registered name of the cairn (preferred). If omitted, the cairn is "
            "linked by relative path instead, and the agent will resolve it via "
            "filesystem rather than the MCP registry."
        ),
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing cairn.toml at the project repo root.",
    ),
) -> None:
    """Pair a project repo with this cairn by writing a cairn.toml pointer."""
    cairn_paths = resolve_or_exit()
    project = project_repo.resolve()
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
                f"warning: '{name}' is not currently registered in your MCP "
                f"registry. Register it with `cairn register {name} {cairn_paths.root}` "
                f"so the MCP server can serve it.",
                err=True,
            )
        elif existing.path.resolve() != cairn_paths.root.resolve():
            typer.echo(
                f"warning: registry says '{name}' points at {existing.path}, "
                f"but you're linking from {cairn_paths.root}. The pointer file "
                f"records the name; the registry is the source of truth for the path.",
                err=True,
            )
        try:
            written = write_pointer(project, name=name)
        except CairnTomlError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from None
        typer.echo(
            f"Linked {project} → cairn '{name}'. Wrote {written}."
        )
        return

    # No --name: link by path.
    if not is_cairn_root(cairn_paths.root):
        typer.echo(
            f"error: {cairn_paths.root} is not a cairn root", err=True
        )
        raise typer.Exit(code=1)
    try:
        written = write_pointer(project, path=cairn_paths.root)
    except CairnTomlError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(
        f"Linked {project} → {cairn_paths.root}. Wrote {written}."
    )
