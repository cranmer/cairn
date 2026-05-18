"""`cairn collaborator add` — register a new collaborator."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import typer
import yaml
from git import Repo
from pydantic import ValidationError

from ..errors import CairnError, CollisionError
from ..git_ops import commit, get_user_identity
from ..io.state_io import load_collaborators, write_collaborators
from ..paths import CairnPaths
from ..schemas import Collaborator
from ._common import resolve_or_exit

app = typer.Typer(no_args_is_help=True, help="Manage cairn collaborators.")


def _check_unique(paths: CairnPaths, new_ids: list[str]) -> None:
    existing = {c.id for c in load_collaborators(paths)}
    duplicates = sorted(set(new_ids) & existing)
    if duplicates:
        word = "id" if len(duplicates) == 1 else "ids"
        raise CollisionError(
            f"collaborator {word} already in use: {', '.join(duplicates)}"
        )
    intra = sorted({x for x in new_ids if new_ids.count(x) > 1})
    if intra:
        word = "id" if len(intra) == 1 else "ids"
        raise CollisionError(f"duplicate {word} within input: {', '.join(intra)}")


def _append_and_commit(
    paths: CairnPaths, new_models: list[Collaborator], summary: str
) -> None:
    existing = load_collaborators(paths)
    combined = existing + new_models
    write_collaborators(paths, combined)
    repo = Repo(paths.root)
    commit(
        repo,
        [paths.collaborators_yaml],
        message=summary,
        author=get_user_identity(repo),
    )


@app.command(name="add")
def add(
    id_: str | None = typer.Option(None, "--id", help="Collaborator id (kebab-case)."),
    name: str | None = typer.Option(None, "--name", help="Display name."),
    role: str | None = typer.Option(
        None,
        "--role",
        help=(
            "What you do on this project, in your own words. Prefer activity-based "
            "phrasing (e.g., 'designing generative models', 'running ablation "
            "experiments', 'maintaining the data pipeline') over titles."
        ),
    ),
    type_: str = typer.Option("human", "--type", help="'human' or 'ai-collaborator'."),
    email: str | None = typer.Option(
        None,
        "--email",
        help=(
            "Email address. Used by the orient skill to match the current git user "
            "against the collaborator list; without it the agent has to ask."
        ),
    ),
    github: str | None = typer.Option(None, "--github", help="GitHub handle."),
    expertise: list[str] = typer.Option(
        [], "--expertise", help="Repeatable; expertise tag.", show_default=False
    ),
    current_focus: str | None = typer.Option(None, "--current-focus"),
    recent_papers: list[str] = typer.Option(
        [], "--recent-paper", help="Repeatable; DOI or citation.", show_default=False
    ),
    notes: str | None = typer.Option(None, "--notes"),
    yaml_file: str | None = typer.Option(
        None, "--yaml", help="Read a YAML list of collaborators from FILE (or '-' for stdin)."
    ),
) -> None:
    """Add one or more collaborators to ``state/collaborators.yaml``."""
    paths = resolve_or_exit()

    new_models: list[Collaborator] = []

    if yaml_file:
        if yaml_file == "-":
            raw = yaml.safe_load(sys.stdin.read())
        else:
            raw = yaml.safe_load(Path(yaml_file).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            typer.echo("error: expected a top-level YAML list of collaborators", err=True)
            raise typer.Exit(code=1)
        try:
            new_models = [Collaborator.model_validate(item) for item in raw]
        except ValidationError as exc:
            typer.echo(f"error: schema validation failed:\n{exc}", err=True)
            raise typer.Exit(code=1) from None
    else:
        if not (id_ and name and role):
            typer.echo(
                "error: --id, --name, and --role are required "
                "(or use --yaml FILE / --yaml - for bulk input)",
                err=True,
            )
            raise typer.Exit(code=1)
        data: dict[str, Any] = {
            "id": id_,
            "name": name,
            "role": role,
            "type": type_,
            "email": email,
            "github": github,
            "expertise": expertise,
            "current_focus": current_focus,
            "recent_papers": recent_papers,
            "notes": notes,
        }
        data = {k: v for k, v in data.items() if v not in (None, [], "")}
        try:
            new_models = [Collaborator.model_validate(data)]
        except ValidationError as exc:
            typer.echo(f"error: schema validation failed:\n{exc}", err=True)
            raise typer.Exit(code=1) from None

    try:
        _check_unique(paths, [m.id for m in new_models])
    except CollisionError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    try:
        if len(new_models) == 1:
            msg = f"Add collaborator '{new_models[0].id}'"
        else:
            ids = ", ".join(m.id for m in new_models)
            msg = f"Add collaborators: {ids}"
        _append_and_commit(paths, new_models, summary=msg)
    except CairnError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    n = len(new_models)
    typer.echo(f"Added {n} collaborator{'' if n == 1 else 's'}.")
