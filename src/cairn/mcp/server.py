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
    write_collaborators,
    write_decisions,
    write_questions,
)
from ..paths import MARKER_FILE, CairnPaths
from ..registry import (
    RegisteredCairn,
    RegistryError,
    load_registry,
    resolve_single_or_named,
)
from ..schemas import ActionItem, Collaborator, Decision, FindingFrontmatter, OpenQuestion
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
    known = {c.id for c in collabs}
    if author not in known:
        suggestion = ""
        if known:
            close = ", ".join(sorted(known))
            suggestion = f" Known ids: {close}."
        raise RegistryError(
            f"unknown author '{author}' in this cairn.{suggestion} "
            f"Register a new collaborator via the `add_collaborator` MCP tool "
            f"(or `cairn collaborator add` on the host CLI)."
        )


def _suggest_collaborator_match(paths: CairnPaths, collabs: list) -> dict[str, Any]:
    """Try to suggest which existing collaborator matches the calling git user."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "config", "--get", "user.email"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        git_email = result.stdout.strip() if result.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        git_email = None

    suggested_id: str | None = None
    if git_email:
        for c in collabs:
            if c.email and c.email.lower() == git_email.lower():
                suggested_id = c.id
                break
        if suggested_id is None:
            # Fall back: github handle vs local-part of the email
            local_part = git_email.split("@", 1)[0].lower()
            for c in collabs:
                if c.github and c.github.lower() == local_part:
                    suggested_id = c.id
                    break

    return {"git_email": git_email, "suggested_id": suggested_id}


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

    @mcp.tool(
        description=(
            "Return the calling client's resolved identity for a cairn. Lists "
            "all registered collaborators plus, if available, a suggested "
            "match against the calling git user (resolved from git config). "
            "If the suggested match is null and your git email looks plausible, "
            "register yourself with `add_collaborator`."
        )
    )
    def whoami(cairn: str | None = None) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        collabs = load_collaborators(paths)
        suggested = _suggest_collaborator_match(paths, collabs)
        return {
            "cairn": entry.name,
            "cairn_path": str(paths.root),
            "git_email": suggested.get("git_email"),
            "suggested_id": suggested.get("suggested_id"),
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
        description=(
            "Record a decision in the cairn (mirrors `cairn decision add`). "
            "`related` is a list of canonical entity IDs (e.g., ['D-003', "
            "'Q-007', 'A-014']) — NOT finding paths or slugs. Each must "
            "resolve in the cairn or the call fails."
        )
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
            "slug": final_slug,
            "date": today,
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

    @mcp.tool(
        description=(
            "Register a new collaborator (mirrors `cairn collaborator add`). "
            "Required for any cairn the first time it's used and whenever a "
            "new contributor joins."
        )
    )
    def add_collaborator(
        id: str,
        name: str,
        role: str,
        cairn: str | None = None,
        type: str = "human",
        email: str | None = None,
        github: str | None = None,
        expertise: list[str] | None = None,
        current_focus: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        existing = load_collaborators(paths)
        if any(c.id == id for c in existing):
            raise RegistryError(f"collaborator id '{id}' is already in use")
        data: dict[str, Any] = {
            "id": id,
            "name": name,
            "role": role,
            "type": type,
            "email": email,
            "github": github,
            "expertise": expertise or [],
            "current_focus": current_focus,
            "notes": notes,
        }
        data = {k: v for k, v in data.items() if v not in (None, [], "")}
        try:
            new_collab = Collaborator.model_validate(data)
        except ValidationError as exc:
            raise RegistryError(f"schema validation failed: {exc}") from None
        combined = [*existing, new_collab]
        write_collaborators(paths, combined)
        repo = Repo(paths.root)
        sha = commit(
            repo,
            [paths.collaborators_yaml],
            message=f"Add collaborator '{id}'",
            author=get_user_identity(repo),
        )
        return {
            "cairn": entry.name,
            "id": id,
            "commit_sha": sha[:12],
        }

    @mcp.tool(
        description=(
            "Record an open question (mirrors a CLI command not yet shipped). "
            "Use when the user surfaces something to investigate or decide."
        )
    )
    def add_open_question(
        raised_by: str,
        question: str,
        cairn: str | None = None,
        related: list[str] | None = None,
    ) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        related = related or []
        _validate_author(paths, raised_by)
        _validate_related(paths, related)
        state = load_state(paths)
        new_id = next_id("Q", state.question_ids())
        now = datetime.now(timezone.utc).replace(microsecond=0)
        try:
            new_q = OpenQuestion.model_validate(
                {
                    "id": new_id,
                    "raised_by": raised_by,
                    "date": now,
                    "question": question,
                    "status": "open",
                    "related": related,
                }
            )
        except ValidationError as exc:
            raise RegistryError(f"schema validation failed: {exc}") from None
        questions = [*load_questions(paths), new_q]
        write_questions(paths, questions)
        repo = Repo(paths.root)
        sha = commit(
            repo,
            [paths.open_questions_yaml],
            message=f"{new_id}: {question[:60]}",
            author=get_user_identity(repo),
        )
        return {
            "cairn": entry.name,
            "id": new_id,
            "commit_sha": sha[:12],
        }

    @mcp.tool(
        description=(
            "Return the cairn's PROJECT.md content (project overview, current "
            "focus, related repositories, etc.)."
        )
    )
    def get_project_md(cairn: str | None = None) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        if not paths.project_md.is_file():
            return {"cairn": entry.name, "exists": False, "content": ""}
        return {
            "cairn": entry.name,
            "exists": True,
            "content": paths.project_md.read_text(encoding="utf-8"),
        }

    @mcp.tool(
        description=(
            "Overwrite the cairn's PROJECT.md with new content. Commits the "
            "change attributed to the given author. Use the standard "
            "read-modify-write pattern: call get_project_md first, modify the "
            "content locally, then call this. There is no section-level edit "
            "API — overwrite is intentional so the agent always reasons about "
            "the whole document."
        )
    )
    def set_project_md(
        author: str,
        content: str,
        cairn: str | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        _validate_author(paths, author)
        if not content.endswith("\n"):
            content += "\n"
        paths.project_md.write_text(content, encoding="utf-8")
        repo = Repo(paths.root)
        sha = commit(
            repo,
            [paths.project_md],
            message=message or "Update PROJECT.md",
            author=get_user_identity(repo),
        )
        return {
            "cairn": entry.name,
            "path": str(paths.project_md.relative_to(paths.root)),
            "commit_sha": sha[:12],
        }

    # ---- Lookup reads (closes the related-ID loop) ------------------------

    @mcp.tool(description="List collaborators for a cairn.")
    def list_collaborators(cairn: str | None = None) -> list[dict[str, Any]]:
        _, paths = _resolve(cairn)
        return [c.model_dump(mode="json") for c in load_collaborators(paths)]

    @mcp.tool(
        description=(
            "List decisions, optionally filtered. Newest first. Useful for "
            "populating `related: ['D-NNN']` on a new write without parsing "
            "files. Pass `query` for substring match on the decision text."
        )
    )
    def list_decisions(
        cairn: str | None = None,
        author: str | None = None,
        query: str | None = None,
        limit: int | None = 20,
    ) -> list[dict[str, Any]]:
        _, paths = _resolve(cairn)
        from ..io.state_io import load_decisions

        decisions = list(reversed(load_decisions(paths)))
        if author:
            decisions = [d for d in decisions if d.author == author]
        if query:
            q = query.lower()
            decisions = [
                d for d in decisions
                if q in d.decision.lower() or (d.context and q in d.context.lower())
            ]
        if limit:
            decisions = decisions[:limit]
        return [d.model_dump(mode="json") for d in decisions]

    @mcp.tool(description="Fetch a single decision by ID.")
    def get_decision(id: str, cairn: str | None = None) -> dict[str, Any]:
        _, paths = _resolve(cairn)
        from ..io.state_io import load_decisions

        for d in load_decisions(paths):
            if d.id == id:
                return d.model_dump(mode="json")
        raise RegistryError(f"no decision with id '{id}'")

    @mcp.tool(
        description=(
            "List findings (summaries only — call get_finding for full body). "
            "Newest first by date+slug. Useful for surfacing recent findings "
            "or building cross-references."
        )
    )
    def list_findings(
        cairn: str | None = None,
        since: str | None = None,
        limit: int | None = 20,
    ) -> list[dict[str, Any]]:
        _, paths = _resolve(cairn)
        from ..io import frontmatter as fm

        if not paths.findings.is_dir():
            return []
        cutoff = date.fromisoformat(since) if since else None
        out: list[dict[str, Any]] = []
        for child in paths.findings.iterdir():
            if not child.is_file() or child.suffix != ".md" or child.name == ".gitkeep":
                continue
            m = FINDING_FILENAME.match(child.name)
            if not m:
                continue
            try:
                data, _ = fm.load(child)
            except (ValueError, OSError):
                continue
            d_str = m.group("date")
            if cutoff:
                try:
                    if date.fromisoformat(d_str) < cutoff:
                        continue
                except ValueError:
                    continue
            out.append(
                {
                    "slug": m.group("slug"),
                    "date": d_str,
                    "title": data.get("title") if isinstance(data, dict) else None,
                    "author": data.get("author") if isinstance(data, dict) else None,
                    "related": data.get("related", []) if isinstance(data, dict) else [],
                    "exploration": data.get("exploration") if isinstance(data, dict) else None,
                    "path": str(child.relative_to(paths.root)),
                }
            )
        out.sort(key=lambda r: (r["date"], r["slug"]), reverse=True)
        if limit:
            out = out[:limit]
        return out

    @mcp.tool(
        description=(
            "Fetch a single finding (frontmatter + full markdown body) "
            "by slug or path."
        )
    )
    def get_finding(
        cairn: str | None = None,
        slug: str | None = None,
        date: str | None = None,
        path: str | None = None,
    ) -> dict[str, Any]:
        _, paths = _resolve(cairn)
        from ..io import frontmatter as fm

        target = None
        if path:
            target = paths.root / path
        elif slug:
            # If date given, exact match; else pick the most recent with that slug.
            candidates = [
                p for p in paths.findings.iterdir()
                if p.is_file() and p.name.endswith(f"-{slug}.md")
            ]
            if date:
                candidates = [p for p in candidates if p.name.startswith(date + "-")]
            if not candidates:
                raise RegistryError(
                    f"no finding with slug '{slug}'"
                    + (f" on {date}" if date else "")
                )
            target = max(candidates, key=lambda p: p.name)
        else:
            raise RegistryError("get_finding requires either `slug` or `path`")
        if not target.is_file():
            raise RegistryError(f"finding not found at {target}")
        data, body = fm.load(target)
        return {
            "path": str(target.relative_to(paths.root)),
            "frontmatter": data,
            "body": body,
        }

    @mcp.tool(
        description=(
            "Mark an open question as answered (mirrors a CLI command not yet "
            "shipped). `answered_by` is a related entity id — typically the "
            "decision that resolved the question (D-NNN), but may be a "
            "finding's slug or another question."
        )
    )
    def resolve_open_question(
        id: str,
        answered_by: str,
        actor: str,
        cairn: str | None = None,
    ) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        _validate_author(paths, actor)
        state = load_state(paths)
        if answered_by not in state.id_index():
            raise RegistryError(f"answered_by refers to unknown entity: {answered_by}")
        questions = load_questions(paths)
        target_idx = next((i for i, q in enumerate(questions) if q.id == id), None)
        if target_idx is None:
            raise RegistryError(f"unknown question id: {id}")
        questions[target_idx] = questions[target_idx].model_copy(
            update={"status": "answered", "answered_by": answered_by}
        )
        from ..io.state_io import write_questions
        write_questions(paths, questions)
        repo = Repo(paths.root)
        sha = commit(
            repo,
            [paths.open_questions_yaml],
            message=f"{id}: answered by {answered_by}",
            author=get_user_identity(repo),
        )
        return {"cairn": entry.name, "id": id, "commit_sha": sha[:12]}

    # ---- Exploration tools (move up from Tier 2) --------------------------

    @mcp.tool(
        description=(
            "Open a cairn exploration — a tracked alternative line of inquiry. "
            "Materialized as a git branch <as_id>/<slug> in the cairn plus a "
            "manifest under explorations/. Use when the user wants the "
            "RATIONALE of an alternative tracked (design alternative, "
            "methodology choice). For ordinary git branching in a project "
            "repo, the user should use git directly — this is a cairn-level "
            "concept."
        )
    )
    def start_exploration(
        description: str,
        as_id: str,
        cairn: str | None = None,
    ) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        _validate_author(paths, as_id)
        # Reuse the CLI helpers — they already handle slug, manifest, commits.
        from ..cli.exploration_cmd import (
            _append_to_explorations_readme,
            _explorations_index_entry,
            _kebab,
            _manifest_body,
        )

        try:
            slug = _kebab(description)
        except ValueError as exc:
            raise RegistryError(str(exc)) from None

        branch_name = f"{as_id}/{slug}"
        repo = Repo(paths.root)
        if branch_name in [h.name for h in repo.heads]:
            raise RegistryError(
                f"exploration '{branch_name}' already exists (git branch present)"
            )

        today = datetime.now(timezone.utc).date().isoformat()
        manifest_path = paths.explorations / as_id / f"{slug}.md"
        # Update explorations/README.md on the current branch
        line = _explorations_index_entry(branch_name, as_id, today, description)
        _append_to_explorations_readme(paths.explorations / "README.md", line)
        commit(
            repo,
            [paths.explorations / "README.md"],
            message=f"Open exploration {branch_name}",
            author=get_user_identity(repo),
        )
        # Create the branch + manifest commit
        new_head = repo.create_head(branch_name)
        new_head.checkout()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            _manifest_body(branch_name, as_id, today, description), encoding="utf-8"
        )
        sha = commit(
            repo,
            [manifest_path],
            message=f"{branch_name}: open exploration manifest",
            author=get_user_identity(repo),
        )
        return {
            "cairn": entry.name,
            "name": branch_name,
            "manifest": str(manifest_path.relative_to(paths.root)),
            "commit_sha": sha[:12],
        }

    @mcp.tool(
        description=(
            "Close a cairn exploration (mirrors `cairn exploration close`). "
            "status must be 'merged' or 'abandoned'. For 'merged', the "
            "exploration's git branch must be an ancestor of main."
        )
    )
    def close_exploration(
        name: str,
        status: str,
        reason: str,
        closed_by: str,
        cairn: str | None = None,
    ) -> dict[str, Any]:
        entry, paths = _resolve(cairn)
        _validate_author(paths, closed_by)
        status = status.lower()
        if status not in {"merged", "abandoned"}:
            raise RegistryError("status must be 'merged' or 'abandoned'")
        if not reason.strip():
            raise RegistryError("reason must not be empty")
        from ..cli.exploration_cmd import (
            _closure_block,
            _is_merged_into_main,
            _move_explorations_readme_row,
            _read_manifest,
            _split_exploration_name,
        )

        owner, slug = _split_exploration_name(name)
        repo = Repo(paths.root)
        if name not in [h.name for h in repo.heads]:
            raise RegistryError(f"exploration '{name}' does not exist locally")
        is_merged, main_name = _is_merged_into_main(repo, name)
        if main_name is None:
            raise RegistryError("could not locate 'main' or 'master' in the cairn")
        if status == "merged" and not is_merged:
            raise RegistryError(
                f"'{name}' is not an ancestor of '{main_name}'; merge first"
            )
        # Switch to main first
        repo.git.checkout(main_name)
        manifest_rel = f"explorations/{owner}/{slug}.md"
        manifest_text = _read_manifest(repo, name, manifest_rel)
        if manifest_text is None:
            raise RegistryError(f"no manifest found for '{name}'")
        closed_at = datetime.now(timezone.utc).date().isoformat()
        merge_sha = repo.commit(name).hexsha[:12] if status == "merged" else None
        closure = _closure_block(status, closed_at, closed_by, reason.strip(), merge_sha)
        updated_manifest = manifest_text.rstrip("\n") + "\n" + closure
        manifest_path = paths.root / manifest_rel
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(updated_manifest, encoding="utf-8")
        readme_path = paths.explorations / "README.md"
        _move_explorations_readme_row(
            readme_path, name, owner, closed_at, status, reason.strip()
        )
        sha = commit(
            repo,
            [readme_path, manifest_path],
            message=f"Close exploration {name} ({status}): {reason.strip()[:60]}",
            author=get_user_identity(repo),
        )
        return {
            "cairn": entry.name,
            "name": name,
            "status": status,
            "merge_sha": merge_sha,
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
