"""`cairn validate` — check schema + cross-references."""

from __future__ import annotations

import typer

from ..validate import run_all
from ._common import require_local_target, resolve_target


def validate(
    strict: bool = typer.Option(
        False, "--strict", help="Treat soft inconsistencies (orphans, missing authors) as warnings."
    ),
) -> None:
    """Validate the cairn at the current location."""
    paths = require_local_target(resolve_target(), "validate")
    report = run_all(paths, strict=strict)
    typer.echo(report.render())
    raise typer.Exit(code=report.exit_code())
