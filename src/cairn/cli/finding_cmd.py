"""`cairn finding add` — log a finding under ``knowledge/findings/``."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import typer
from git import Repo
from pydantic import ValidationError

from ..errors import CairnError
from ..git_ops import commit, get_user_identity
from ..io.frontmatter import write as write_frontmatter
from ..io.state_io import load_state
from ..schemas import FindingFrontmatter
from ._common import RemoteTarget, resolve_or_exit_with_remote

app = typer.Typer(no_args_is_help=True, help="Log findings under knowledge/findings/.")


_SLUG_BAD = re.compile(r"[^a-z0-9]+")


def _kebab(text: str) -> str:
    text = text.lower().strip()
    slug = _SLUG_BAD.sub("-", text).strip("-")
    if not slug:
        raise ValueError("could not derive a slug from the given title or slug input")
    return slug[:60]


def _current_branch(repo: Repo) -> str | None:
    try:
        return repo.active_branch.name
    except TypeError:  # detached HEAD
        return None


@app.command(name="add")
def add(
    author: str = typer.Option(..., "--author", help="Collaborator id of the finding's author."),
    title: str = typer.Option(..., "--title", help="One-line statement of the finding."),
    slug: str | None = typer.Option(
        None,
        "--slug",
        help="Kebab-case slug for the filename. Defaults to a kebab of --title.",
    ),
    related: list[str] = typer.Option(
        [], "--related", help="Repeatable; IDs of related entities (Q-NNN, D-NNN, ...)."
    ),
    body: str | None = typer.Option(None, "--body", help="Finding body text (markdown)."),
    body_from: Path | None = typer.Option(
        None,
        "--body-from",
        help="Read finding body from this file. Mutually exclusive with --body.",
    ),
    no_commit: bool = typer.Option(
        False, "--no-commit", help="Write the file but don't stage or commit it."
    ),
) -> None:
    """Write ``knowledge/findings/YYYY-MM-DD-<slug>.md`` with YAML frontmatter."""
    target = resolve_or_exit_with_remote()

    if body is not None and body_from is not None:
        typer.echo("error: --body and --body-from are mutually exclusive", err=True)
        raise typer.Exit(code=1)

    body_text = body
    if body_from is not None:
        try:
            body_text = body_from.read_text(encoding="utf-8")
        except OSError as exc:
            typer.echo(f"error: could not read --body-from: {exc}", err=True)
            raise typer.Exit(code=1) from None

    try:
        final_slug = _kebab(slug or title)
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    # --- Remote dispatch -------------------------------------------------------
    if isinstance(target, RemoteTarget):
        from ..mcp.remote import RemoteDispatchError, dispatch_tool

        args: dict = {"author": author, "title": title, "slug": final_slug}
        if related:
            args["related"] = list(related)
        if body_text is not None:
            args["body"] = body_text
        try:
            result = dispatch_tool(target.endpoint, target.cairn_name, "add_finding", args)
        except RemoteDispatchError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from None
        typer.echo(
            f"Logged finding '{final_slug}' "
            f"(via remote cairn at {target.endpoint})."
        )
        if "path" in result:
            typer.echo(f"  path: {result['path']}")
        return

    # --- Local dispatch -------------------------------------------------------
    paths = target
    state = load_state(paths)

    if author not in state.collaborator_ids():
        typer.echo(
            f"error: unknown author '{author}'. "
            f"Register with `cairn collaborator add` first.",
            err=True,
        )
        raise typer.Exit(code=1)

    id_index = state.id_index()
    bad_refs = [r for r in related if r not in id_index]
    if bad_refs:
        typer.echo(
            f"error: --related refers to unknown entity ids: {', '.join(bad_refs)}",
            err=True,
        )
        raise typer.Exit(code=1)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    date_str = now.date().isoformat()
    filename = f"{date_str}-{final_slug}.md"
    target_file = paths.findings / filename
    if target_file.exists():
        typer.echo(
            f"error: {target_file.relative_to(paths.root)} already exists. "
            f"Pick a different slug.",
            err=True,
        )
        raise typer.Exit(code=1)

    repo = Repo(paths.root)
    exploration = _current_branch(repo)

    try:
        validated = FindingFrontmatter.model_validate(
            {
                "date": now,
                "author": author,
                "title": title,
                "slug": final_slug,
                "related": related,
                "exploration": exploration,
            }
        )
    except ValidationError as exc:
        typer.echo(f"error: schema validation failed:\n{exc}", err=True)
        raise typer.Exit(code=1) from None

    fm = validated.model_dump(mode="json", exclude_none=False)
    body_to_write = (
        body_text.rstrip("\n") + "\n"
        if body_text
        else f"# {title}\n\nTODO: write up the finding.\n"
    )
    try:
        write_frontmatter(target_file, fm, body_to_write)
    except OSError as exc:
        typer.echo(f"error: could not write finding file: {exc}", err=True)
        raise typer.Exit(code=1) from None

    if no_commit:
        typer.echo(f"Wrote {target_file.relative_to(paths.root)} (not committed; --no-commit).")
        return

    try:
        commit(
            repo,
            [target_file],
            message=f"Log finding: {title[:60]}",
            author=get_user_identity(repo),
        )
    except CairnError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Logged finding at {target_file.relative_to(paths.root)}.")
