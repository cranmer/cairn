"""`cairn branch start` — create an exploration branch with a manifest."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import typer
from git import Repo

from ..errors import CairnError
from ..git_ops import commit, get_user_identity
from ..io.state_io import load_collaborators
from ._common import resolve_or_exit

app = typer.Typer(no_args_is_help=True, help="Manage exploration branches.")


_SLUG_BAD = re.compile(r"[^a-z0-9]+")


def _kebab(text: str) -> str:
    text = text.lower().strip()
    slug = _SLUG_BAD.sub("-", text).strip("-")
    if not slug:
        raise ValueError("description produced an empty slug")
    return slug[:50]


def _branches_index_entry(branch_name: str, owner: str, date_str: str, purpose: str) -> str:
    return f"| `{branch_name}` | {owner} | {date_str} | {purpose} |\n"


def _append_to_branches_readme(readme: Path, line: str) -> None:
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    if not text.endswith("\n"):
        text += "\n"
    readme.write_text(text + line, encoding="utf-8")


def _manifest_body(branch_name: str, owner: str, date_str: str, description: str) -> str:
    return (
        f"# Branch manifest: `{branch_name}`\n\n"
        f"- **Owner**: {owner}\n"
        f"- **Opened**: {date_str}\n"
        f"- **Branch**: `{branch_name}`\n\n"
        f"## Proposed line of inquiry\n\n"
        f"{description}\n\n"
        f"## Initial rationale\n\n"
        f"TODO: Why this is worth exploring now and what would make it merge-worthy.\n"
    )


@app.command(name="start")
def start(
    description: str = typer.Argument(..., help="Short description of the exploration goal."),
    as_id: str | None = typer.Option(
        None,
        "--as",
        help="Collaborator id to attribute the branch to. "
        "Defaults to the only collaborator if there is exactly one.",
    ),
) -> None:
    """Create `<user-id>/<kebab>` branch, write a manifest, and update the index."""
    paths = resolve_or_exit()
    collabs = load_collaborators(paths)
    known_ids = {c.id for c in collabs}

    if as_id is None:
        if len(collabs) == 1:
            as_id = collabs[0].id
        else:
            typer.echo(
                "error: --as <collaborator-id> is required when there is more than one "
                "(or zero) collaborator registered. Add collaborators with "
                "`cairn collaborator add`.",
                err=True,
            )
            raise typer.Exit(code=1)
    if as_id not in known_ids:
        typer.echo(
            f"error: unknown collaborator '{as_id}'. "
            f"Register with `cairn collaborator add` first.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        slug = _kebab(description)
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    branch_name = f"{as_id}/{slug}"
    repo = Repo(paths.root)

    if branch_name in [h.name for h in repo.heads]:
        typer.echo(
            f"error: branch '{branch_name}' already exists. "
            f"Pick a different description or delete the existing branch first.",
            err=True,
        )
        raise typer.Exit(code=1)

    today = datetime.now(UTC).date().isoformat()
    manifest_path = paths.branches / as_id / f"{slug}.md"

    # 1. Update branches/README.md on the current branch (typically main).
    manifest_rel = manifest_path.relative_to(paths.root)
    line = _branches_index_entry(branch_name, as_id, today, description)
    _append_to_branches_readme(paths.branches / "README.md", line)
    try:
        commit(
            repo,
            [paths.branches / "README.md"],
            message=f"Open branch {branch_name}",
            author=get_user_identity(repo),
        )
    except CairnError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    # 2. Create the new branch, switch to it, and add the manifest commit.
    new_head = repo.create_head(branch_name)
    new_head.checkout()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        _manifest_body(branch_name, as_id, today, description), encoding="utf-8"
    )
    try:
        commit(
            repo,
            [manifest_path],
            message=f"{branch_name}: open branch manifest",
            author=get_user_identity(repo),
        )
    except CairnError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo(
        f"Opened branch '{branch_name}'. Manifest at {manifest_rel}. You are on the new branch."
    )
