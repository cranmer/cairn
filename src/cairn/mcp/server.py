"""FastMCP server exposing Tier-1 cairn tools.

Tier-1 tools (per ADR-0009):
- whoami
- status
- get_open_questions
- get_action_items
- add_decision
- add_finding
- add_action
- complete_action

Every tool takes a ``cairn`` parameter naming the target cairn (per
ADR-0010). When the registry has exactly one cairn, the parameter
defaults to that one; otherwise it's required.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from git import Repo

# Import FastMCP at module-import time — this module is only imported when
# the user actually runs `cairn mcp`, which already requires the [mcp] extra.
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from ..errors import CairnError
from ..git_ops import commit, get_user_identity
from ..ids import next_id
from ..io.frontmatter import dump as frontmatter_dump
from ..io.state_io import (
    load_actions,
    load_collaborators,
    load_questions,
    load_state,
    write_actions,
    write_decisions,
)
from ..paths import MARKER_FILE, CairnPaths
from ..registry import (
    RegisteredCairn,
    RegistryError,
    load_registry,
    resolve_single_or_named,
)
from ..schemas import ActionItem, Decision, FindingFrontmatter
from ..schemas.findings import FINDING_FILENAME
from ..status.render import render_json
from ..status.snapshot import build_status, state_for_branch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve(cairn: str | None) -> tuple[RegisteredCairn, CairnPaths]:
    """Resolve a cairn parameter to (registry entry, CairnPaths)."""
    entry = resolve_single_or_named(cairn)
    return entry, CairnPaths(root=entry.path)


def _validate_author(paths: CairnPaths, author: str) -> None:
    collabs = load_collaborators(paths)
    if author not in {c.id for c in collabs}:
        raise RegistryError(
            f"unknown author '{author}' in this cairn. Register a collaborator "
            f"with `cairn collaborator add` first."
        )


def _validate_related(paths: CairnPaths, related: list[str]) -> None:
    if not related:
        return
    state = load_state(paths)
    id_index = state.id_index()
    bad = [r for r in related if r not in id_index]
    if bad:
        raise RegistryError(
            f"--related refers to unknown entity ids: {', '.join(bad)}"
        )


def _slugify(text: str) -> str:
    import re
    s = re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")
    return s[:60] or "untitled"


# ---------------------------------------------------------------------------
# FastMCP server + tool definitions
# ---------------------------------------------------------------------------


def build_server() -> FastMCP:
    """Construct the FastMCP server and register the Tier-1 tools."""
    mcp = FastMCP(
        name="cairn",
        instructions=(
            "Cairn MCP server — exposes cairn read/write operations for one or "
            "more registered cairns. Every tool accepts a `cairn` parameter "
            "naming the target. When only one cairn is registered, `cairn` "
            "defaults to it. List registered cairns with `cairn registered` "
            "on the host CLI."
        ),
    )

    # ---- Identity / status ------------------------------------------------

    @mcp.tool(description="Return the calling client's resolved identity for a cairn.")
    def whoami(cairn: str | None = None) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        collabs = load_collaborators(paths)
        # The MCP server does not authenticate clients in v0; whoami reports
        # the cairn's registered collaborators so the caller can pick its id.
        return {
            "cairn": entry.name,
            "cairn_path": str(paths.root),
            "collaborators": [
                {"id": c.id, "name": c.name, "email": c.email, "github": c.github}
                for c in collabs
            ],
        }

    @mcp.tool(description="Compact project-state summary for a cairn.")
    def status(cairn: str | None = None) -> dict[str, Any]:
        _, paths = _resolve(cairn)
        state = state_for_branch(paths, None)
        snap = build_status(paths, state, branch="current")
        import json
        return json.loads(render_json(snap))

    # ---- Reads ------------------------------------------------------------

    @mcp.tool(description="List open questions for a cairn.")
    def get_open_questions(
        cairn: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        _, paths = _resolve(cairn)
        questions = load_questions(paths)
        result = [q.model_dump(mode="json") for q in questions]
        if limit:
            result = result[:limit]
        return result

    @mcp.tool(description="List action items for a cairn, optionally filtered.")
    def get_action_items(
        cairn: str | None = None,
        assignee: str | None = None,
        status: str | None = None,
        due_before: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        _, paths = _resolve(cairn)
        actions = load_actions(paths)
        out: list[ActionItem] = []
        cutoff = date.fromisoformat(due_before) if due_before else None
        for a in actions:
            if assignee and a.assignee != assignee:
                continue
            if status and a.status != status:
                continue
            if cutoff and (a.due_date is None or a.due_date > cutoff):
                continue
            out.append(a)
        result = [a.model_dump(mode="json") for a in out]
        if limit:
            result = result[:limit]
        return result

    # ---- Writes -----------------------------------------------------------

    @mcp.tool(
        description="Record a decision in the cairn (mirrors `cairn decision add`)."
    )
    def add_decision(
        author: str,
        text: str,
        cairn: str | None = None,
        context: str | None = None,
        related: list[str] | None = None,
        supersedes: str | None = None,
    ) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        related = related or []
        _validate_author(paths, author)
        _validate_related(paths, related)
        state = load_state(paths)
        if supersedes is not None and not any(
            d.id == supersedes for d in state.decisions
        ):
            raise RegistryError(f"--supersedes refers to unknown decision: {supersedes}")

        new_id = next_id("D", state.decision_ids())
        now = datetime.now(timezone.utc).replace(microsecond=0)
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
            raise RegistryError(f"schema validation failed: {exc}") from None

        decisions = list(state.decisions)
        if supersedes:
            for idx, d in enumerate(decisions):
                if d.id == supersedes:
                    decisions[idx] = d.model_copy(update={"superseded_by": new_id})
                    break
        decisions.append(new_decision)

        write_decisions(paths, decisions)
        repo = Repo(paths.root)
        sha = commit(
            repo,
            [paths.decisions_yaml],
            message=f"{new_id}: {text[:60]}",
            author=get_user_identity(repo),
        )
        return {
            "cairn": entry.name,
            "id": new_id,
            "commit_sha": sha[:12],
            "path": str(paths.decisions_yaml.relative_to(paths.root)),
        }

    @mcp.tool(
        description="Add a finding to the cairn (mirrors `cairn finding add`)."
    )
    def add_finding(
        author: str,
        title: str,
        cairn: str | None = None,
        body: str | None = None,
        related: list[str] | None = None,
        slug: str | None = None,
    ) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        related = related or []
        _validate_author(paths, author)
        _validate_related(paths, related)

        repo = Repo(paths.root)
        try:
            exploration = repo.active_branch.name
        except Exception:
            exploration = None

        final_slug = slug or _slugify(title)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        today = now.date().isoformat()
        filename = f"{today}-{final_slug}.md"
        if not FINDING_FILENAME.match(filename):
            raise RegistryError(
                f"resulting filename '{filename}' violates finding naming convention"
            )

        target = paths.findings / filename
        if target.exists():
            raise RegistryError(f"finding file already exists: {target.name}")

        try:
            fm = FindingFrontmatter.model_validate(
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
            raise RegistryError(f"schema validation failed: {exc}") from None

        body_text = body or f"# {title}\n\nTODO: write up the finding.\n"
        if not body_text.endswith("\n"):
            body_text += "\n"
        fm_dict = fm.model_dump(mode="json", exclude_none=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(frontmatter_dump(fm_dict, body_text), encoding="utf-8")

        sha = commit(
            repo,
            [target],
            message=f"Log finding {today}-{final_slug}",
            author=get_user_identity(repo),
        )
        return {
            "cairn": entry.name,
            "path": str(target.relative_to(paths.root)),
            "commit_sha": sha[:12],
            "exploration": exploration,
        }

    @mcp.tool(description="Add an action item (mirrors `cairn action add`).")
    def add_action(
        text: str,
        assignee: str,
        cairn: str | None = None,
        due_date: str | None = None,
        related: list[str] | None = None,
    ) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        related = related or []
        _validate_author(paths, assignee)
        _validate_related(paths, related)

        state = load_state(paths)
        new_id = next_id("A", state.action_ids())
        now = datetime.now(timezone.utc).replace(microsecond=0)
        try:
            new_action = ActionItem.model_validate(
                {
                    "id": new_id,
                    "created": now,
                    "assignee": assignee,
                    "text": text,
                    "due_date": due_date,
                    "related": related,
                    "status": "open",
                }
            )
        except ValidationError as exc:
            raise RegistryError(f"schema validation failed: {exc}") from None

        actions = [*load_actions(paths), new_action]
        write_actions(paths, actions)
        repo = Repo(paths.root)
        sha = commit(
            repo,
            [paths.action_items_yaml],
            message=f"{new_id}: {text[:60]}",
            author=get_user_identity(repo),
        )
        return {
            "cairn": entry.name,
            "id": new_id,
            "commit_sha": sha[:12],
        }

    @mcp.tool(description="Mark an action item complete (mirrors `cairn action complete`).")
    def complete_action(
        id: str,
        by: str,
        cairn: str | None = None,
    ) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        _validate_author(paths, by)

        actions = load_actions(paths)
        target_idx = next((i for i, a in enumerate(actions) if a.id == id), None)
        if target_idx is None:
            raise RegistryError(f"unknown action id: {id}")
        action = actions[target_idx]
        if action.status == "complete":
            raise RegistryError(f"action {id} is already complete")

        now = datetime.now(timezone.utc).replace(microsecond=0)
        actions[target_idx] = action.model_copy(
            update={
                "status": "complete",
                "completed_at": now,
                "completed_by": by,
            }
        )
        write_actions(paths, actions)
        repo = Repo(paths.root)
        sha = commit(
            repo,
            [paths.action_items_yaml],
            message=f"Complete {id}",
            author=get_user_identity(repo),
        )
        return {
            "cairn": entry.name,
            "id": id,
            "commit_sha": sha[:12],
        }

    return mcp


def _ensure_registry_loadable() -> None:
    """Validate that the registry file (if present) is parseable at startup."""
    try:
        load_registry()
    except RegistryError as exc:
        # Re-raise as a generic exception so the CLI launcher can surface it.
        raise RuntimeError(str(exc)) from None


def run() -> None:
    """Entry point for `cairn mcp`. Runs the server over stdio."""
    _ensure_registry_loadable()
    server = build_server()
    server.run()  # stdio is FastMCP's default


# Silence unused-import linting from helpers imported only for re-export.
_ = (CairnError, MARKER_FILE)
