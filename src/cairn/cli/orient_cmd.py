"""`cairn orient` — print the project overview + compact status.

Mirrors what the bundled `orient` skill does when an agent starts a session:
read PROJECT.md, then summarize current state. Useful for humans
("what is this project?") and CI scripts. No filtering, no flags — one
shot of context.
"""

from __future__ import annotations

import typer

from ..status import build_status, render_text
from ..status.snapshot import state_for_branch
from ._common import resolve_or_exit


def orient() -> None:
    """Print PROJECT.md and the compact project status in one go."""
    paths = resolve_or_exit()
    if paths.project_md.is_file():
        typer.echo(paths.project_md.read_text(encoding="utf-8").rstrip())
    else:
        typer.echo(f"(no PROJECT.md found at {paths.project_md})")
    typer.echo("\n" + ("-" * 60) + "\n")
    state = state_for_branch(paths, None)
    snap = build_status(paths, state, branch="current")
    typer.echo(render_text(snap))
