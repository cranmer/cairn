"""`cairn status` — compact summary of project state."""

from __future__ import annotations

import typer

from ..status import build_status, render_json, render_text
from ..status.snapshot import state_for_branch
from ._common import resolve_or_exit


def status(
    as_json: bool = typer.Option(False, "--json", help="Emit structured JSON."),
    branch: str | None = typer.Option(
        None, "--branch", help="View a specific branch (defaults to the current cwd's state files)."
    ),
) -> None:
    """Print a compact summary of the project's current state."""
    paths = resolve_or_exit()
    state = state_for_branch(paths, branch)
    branch_label = branch or "current"
    snap = build_status(paths, state, branch=branch_label)
    if as_json:
        typer.echo(render_json(snap))
    else:
        typer.echo(render_text(snap))
