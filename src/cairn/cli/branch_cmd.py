"""`cairn branch start` and `cairn branch close` — exploration branch lifecycle."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import typer
from git import GitCommandError, Repo

from ..errors import CairnError
from ..git_ops import commit, get_user_identity
from ..io.state_io import load_collaborators
from ._common import resolve_or_exit

app = typer.Typer(no_args_is_help=True, help="Manage exploration branches.")


_SLUG_BAD = re.compile(r"[^a-z0-9]+")

ACTIVE_HEADING = "# Active branches"
CLOSED_HEADING = "## Closed branches"
CLOSED_TABLE_HEADER = (
    "| Branch | Owner | Closed | Status | Reason |\n|--------|-------|--------|--------|--------|"
)


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

    today = datetime.now(timezone.utc).date().isoformat()
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


# --- close --------------------------------------------------------------------


def _split_branch(name: str) -> tuple[str, str]:
    """Return (owner, slug) for a branch named ``<owner>/<slug>``."""
    if "/" not in name:
        raise ValueError(
            f"branch '{name}' is not a Cairn exploration branch (expected <owner>/<slug>)"
        )
    owner, _, slug = name.partition("/")
    return owner, slug


def _read_manifest(repo: Repo, branch_name: str, manifest_rel: str) -> str | None:
    """Try to read the manifest file from the branch (or from main if already merged)."""
    for ref in (branch_name, "main", "master"):
        try:
            return repo.git.show(f"{ref}:{manifest_rel}")
        except GitCommandError:
            continue
    return None


def _is_merged_into_main(repo: Repo, branch_name: str) -> tuple[bool, str | None]:
    """Return (is_merged, main_branch_name) — main is whichever of main/master exists."""
    main_name = None
    for candidate in ("main", "master"):
        if candidate in [h.name for h in repo.heads]:
            main_name = candidate
            break
    if main_name is None:
        return False, None
    try:
        repo.git.merge_base("--is-ancestor", branch_name, main_name)
        return True, main_name
    except GitCommandError:
        return False, main_name


def _closure_block(
    status: str, closed_at: str, closed_by: str, reason: str, merge_sha: str | None
) -> str:
    lines = [
        "",
        "## Closure",
        "",
        f"- **Status**: {status}",
        f"- **Closed**: {closed_at}",
        f"- **Closed by**: {closed_by}",
        f"- **Reason**: {reason}",
    ]
    if merge_sha:
        lines.append(f"- **Merge commit**: {merge_sha}")
    lines.append("")
    return "\n".join(lines)


def _move_branches_readme_row(
    readme_path: Path,
    branch_name: str,
    owner: str,
    closed_at: str,
    status: str,
    reason: str,
) -> bool:
    """Remove ``branch_name``'s row from the active table and add it to the closed section.

    Returns True if a row was actually removed (the branch was listed as active),
    False otherwise. The closed section is created on demand.
    """
    text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    needle = f"`{branch_name}`"
    lines = text.splitlines()

    removed = False
    out: list[str] = []
    for line in lines:
        if not removed and needle in line and line.lstrip().startswith("|"):
            removed = True
            continue
        out.append(line)
    new_text = "\n".join(out)
    if new_text and not new_text.endswith("\n"):
        new_text += "\n"

    closed_row = (
        f"| `{branch_name}` | {owner} | {closed_at} | {status} | "
        f"{reason.replace('|', ' ').strip()} |"
    )

    if CLOSED_HEADING in new_text:
        # Append the row at the end (under the existing closed section).
        new_text = new_text.rstrip("\n") + "\n" + closed_row + "\n"
    else:
        if not new_text.endswith("\n"):
            new_text += "\n"
        new_text += "\n" + CLOSED_HEADING + "\n\n" + CLOSED_TABLE_HEADER + "\n" + closed_row + "\n"

    readme_path.write_text(new_text, encoding="utf-8")
    return removed


@app.command(name="close")
def close(
    branch_name: str = typer.Argument(
        ..., help="Branch to close, e.g. 'kyle/try-alt-loss'. Must be `<owner>/<slug>`."
    ),
    status: str = typer.Option(
        ..., "--status", help="Outcome: 'merged' or 'abandoned'.", case_sensitive=False
    ),
    reason: str = typer.Option(
        ..., "--reason", help="Short closure note explaining the outcome."
    ),
    closed_by: str | None = typer.Option(
        None,
        "--closed-by",
        help="Collaborator id closing the branch. "
        "Defaults to the only collaborator if there is exactly one.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Close even if the working tree has uncommitted changes.",
    ),
) -> None:
    """Record the outcome of an exploration branch (merged or abandoned)."""
    paths = resolve_or_exit()
    status = status.lower()
    if status not in {"merged", "abandoned"}:
        typer.echo(f"error: --status must be 'merged' or 'abandoned', got '{status}'", err=True)
        raise typer.Exit(code=1)
    if not reason.strip():
        typer.echo("error: --reason must not be empty", err=True)
        raise typer.Exit(code=1)

    try:
        owner, slug = _split_branch(branch_name)
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    collabs = load_collaborators(paths)
    known_ids = {c.id for c in collabs}
    if closed_by is None:
        if len(collabs) == 1:
            closed_by = collabs[0].id
        else:
            typer.echo(
                "error: --closed-by <collaborator-id> is required when there is more than "
                "one (or zero) collaborator registered.",
                err=True,
            )
            raise typer.Exit(code=1)
    if closed_by not in known_ids:
        typer.echo(f"error: unknown collaborator '{closed_by}'", err=True)
        raise typer.Exit(code=1)

    repo = Repo(paths.root)
    if branch_name not in [h.name for h in repo.heads]:
        typer.echo(f"error: branch '{branch_name}' does not exist locally", err=True)
        raise typer.Exit(code=1)

    if not force and repo.is_dirty(untracked_files=False):
        typer.echo(
            "error: working tree has uncommitted changes; commit or stash them first, "
            "or pass --force.",
            err=True,
        )
        raise typer.Exit(code=1)

    is_merged, main_name = _is_merged_into_main(repo, branch_name)
    if main_name is None:
        typer.echo("error: could not locate a 'main' or 'master' branch in this repo", err=True)
        raise typer.Exit(code=1)
    if status == "merged" and not is_merged:
        typer.echo(
            f"error: --status merged refused: '{branch_name}' is not an ancestor of "
            f"'{main_name}'. Merge it into {main_name} first, then re-run.",
            err=True,
        )
        raise typer.Exit(code=1)

    active_branch_name = repo.active_branch.name if not repo.head.is_detached else None
    if active_branch_name != main_name:
        typer.echo(
            f"error: switch to '{main_name}' before closing a branch "
            f"(currently on '{active_branch_name or 'detached HEAD'}').",
            err=True,
        )
        raise typer.Exit(code=1)

    manifest_rel = f"branches/{owner}/{slug}.md"
    manifest_text = _read_manifest(repo, branch_name, manifest_rel)
    if manifest_text is None:
        typer.echo(
            f"error: no manifest found for '{branch_name}' "
            f"(expected at {manifest_rel} on the branch or on {main_name})",
            err=True,
        )
        raise typer.Exit(code=1)

    closed_at = datetime.now(timezone.utc).date().isoformat()
    merge_sha: str | None = None
    if status == "merged":
        try:
            merge_sha = repo.commit(branch_name).hexsha[:12]
        except (GitCommandError, ValueError):
            merge_sha = None
    closure = _closure_block(status, closed_at, closed_by, reason.strip(), merge_sha)
    updated_manifest = manifest_text.rstrip("\n") + "\n" + closure

    manifest_path = paths.root / manifest_rel
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(updated_manifest, encoding="utf-8")

    readme_path = paths.branches / "README.md"
    _move_branches_readme_row(
        readme_path, branch_name, owner, closed_at, status, reason.strip()
    )

    try:
        commit(
            repo,
            [readme_path, manifest_path],
            message=f"Close branch {branch_name} ({status}): {reason.strip()[:60]}",
            author=get_user_identity(repo),
        )
    except CairnError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo(
        f"Closed '{branch_name}' as {status}. "
        f"Manifest updated at {manifest_rel}; index updated in branches/README.md."
    )
