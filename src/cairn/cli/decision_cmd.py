"""`cairn decision add` — record a decision."""

from __future__ import annotations

from datetime import UTC, datetime

import typer
from git import Repo
from pydantic import ValidationError

from ..errors import CairnError, RefError
from ..git_ops import commit, get_user_identity
from ..ids import next_id
from ..io.state_io import load_state, write_decisions
from ..schemas import Decision
from ._common import resolve_or_exit

app = typer.Typer(no_args_is_help=True, help="Manage decisions.")


@app.command(name="add")
def add(
    author: str = typer.Option(..., "--author", help="Collaborator id of the decision's author."),
    text: str = typer.Option(..., "--text", help="The decision itself, in one or two sentences."),
    context: str | None = typer.Option(
        None, "--context", help="Optional background / rationale / alternatives."
    ),
    related: list[str] = typer.Option(
        [], "--related", help="Repeatable; IDs of related entities (Q-NNN, D-NNN, ...)."
    ),
    supersedes: str | None = typer.Option(
        None, "--supersedes", help="ID of a prior decision this one supersedes."
    ),
) -> None:
    """Record a decision in ``state/decisions.yaml``."""
    paths = resolve_or_exit()
    state = load_state(paths)

    if author not in state.collaborator_ids():
        typer.echo(
            f"error: unknown author '{author}'. "
            f"Add the collaborator first with `cairn collaborator add`.",
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

    superseded: Decision | None = None
    if supersedes:
        for d in state.decisions:
            if d.id == supersedes:
                superseded = d
                break
        if superseded is None:
            typer.echo(f"error: --supersedes refers to unknown decision: {supersedes}", err=True)
            raise typer.Exit(code=1)

    new_id = next_id("D", state.decision_ids())
    now = datetime.now(UTC).replace(microsecond=0)
    try:
        new_decision = Decision.model_validate(
            {
                "id": new_id,
                "date": now,
                "author": author,
                "decision": text,
                "context": context,
                "related": related,
                "supersedes": supersedes,
            }
        )
    except ValidationError as exc:
        typer.echo(f"error: schema validation failed:\n{exc}", err=True)
        raise typer.Exit(code=1) from None

    decisions = list(state.decisions)
    if superseded is not None:
        for idx, d in enumerate(decisions):
            if d.id == superseded.id:
                decisions[idx] = d.model_copy(update={"superseded_by": new_id})
                break
    decisions.append(new_decision)

    try:
        write_decisions(paths, decisions)
        repo = Repo(paths.root)
        commit(
            repo,
            [paths.decisions_yaml],
            message=f"{new_id}: {text[:60]}",
            author=get_user_identity(repo),
        )
    except CairnError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None
    except RefError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Recorded {new_id}.")
