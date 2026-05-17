"""`cairn validate` — check schema + cross-references."""

from __future__ import annotations

import typer

from ..validate import run_all
from ._common import resolve_or_exit


def validate(
    strict: bool = typer.Option(
        False, "--strict", help="Treat soft inconsistencies (orphans, missing authors) as warnings."
    ),
) -> None:
    """Validate the cairn at the current location."""
    paths = resolve_or_exit()
    report = run_all(paths, strict=strict)
    typer.echo(report.render())
    raise typer.Exit(code=report.exit_code())
