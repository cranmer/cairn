"""`cairn skills sync` — copy bundled SKILL.md files into an existing cairn.

Existing cairns scaffolded by an older `cairn init` only have the skills
that shipped with the version they were created from. When new skills
ship in the template (e.g., `bootstrap_from_repo`), this command pulls
them into the current cairn's `skills/` directory so its agents can
discover them via `list_skills`.

Default behavior: only copy skills the current cairn doesn't already
have. Pass `--force` to overwrite existing skills the user has hand-
edited (rarely what you want).
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..git_ops import commit, get_user_identity
from ..template.render import default_template_root
from ._common import require_local_target, resolve_target

app = typer.Typer(no_args_is_help=True, help="Manage the cairn's bundled skills.")


def _bundled_skills_dir() -> Path:
    """Return the bundled-skills source directory inside the installed package."""
    root = default_template_root()
    inner = root / "{{cookiecutter.project_name}}" / "skills"
    if not inner.is_dir():
        raise FileNotFoundError(
            f"bundled skills directory not found: {inner}"
        )
    return inner


@app.command(name="sync")
def sync(
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite skills already present in the cairn (default: skip them).",
    ),
    no_commit: bool = typer.Option(
        False,
        "--no-commit",
        help="Stage the new files but skip the git commit.",
    ),
) -> None:
    """Copy any newly-bundled skills from the installed cairn package into this cairn."""
    paths = require_local_target(resolve_target(), "skills sync")
    source = _bundled_skills_dir()
    target_root = paths.skills

    target_root.mkdir(parents=True, exist_ok=True)
    bundled = [p for p in sorted(source.iterdir()) if p.is_dir()]

    if not bundled:
        typer.echo("No bundled skills found in the installed cairn package.")
        return

    added: list[Path] = []
    overwritten: list[Path] = []
    skipped: list[str] = []

    import shutil

    for skill_dir in bundled:
        name = skill_dir.name
        dest = target_root / name
        already_present = dest.exists()
        if already_present and not force:
            skipped.append(name)
            continue
        if already_present:
            shutil.rmtree(dest)
            overwritten.append(dest)
        else:
            added.append(dest)
        shutil.copytree(skill_dir, dest)

    if not added and not overwritten:
        if skipped:
            typer.echo(
                f"All {len(skipped)} bundled skills are already present in this cairn. "
                f"Re-run with --force to overwrite."
            )
        else:
            typer.echo("No changes needed.")
        return

    # Summarize first; commit only the new/overwritten directories.
    summary_lines = []
    if added:
        summary_lines.append(f"  Added: {', '.join(p.name for p in added)}")
    if overwritten:
        summary_lines.append(f"  Overwritten (--force): {', '.join(p.name for p in overwritten)}")
    if skipped:
        summary_lines.append(f"  Skipped (already present): {', '.join(skipped)}")
    typer.echo("Synced bundled skills into " + str(target_root) + ":")
    for line in summary_lines:
        typer.echo(line)

    if no_commit:
        return

    # Commit the changed files.
    from git import Repo

    repo = Repo(paths.root)
    # commit() expects file paths, not directories — collect everything under each.
    files_to_commit: list[Path] = []
    for skill_dir in (*added, *overwritten):
        for child in skill_dir.rglob("*"):
            if child.is_file():
                files_to_commit.append(child)
    try:
        commit(
            repo,
            files_to_commit,
            message=f"Sync bundled skills ({len(added)} added, {len(overwritten)} overwritten)",
            author=get_user_identity(repo),
        )
    except Exception as exc:
        typer.echo(f"warning: skills copied but commit failed: {exc}", err=True)
