"""Compute a project-status snapshot from CairnState + git."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import yaml
from git import Repo
from pydantic import TypeAdapter

from ..paths import CairnPaths
from ..schemas import ActionItem, CairnState, Collaborator, Decision, Goal, OpenQuestion

MEETING_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


@dataclass
class BranchSummary:
    name: str
    owner: str | None
    last_commit: str  # ISO date


@dataclass
class ActionBreakdown:
    overdue: int = 0
    due_this_week: int = 0
    upcoming: int = 0
    no_due_date: int = 0


@dataclass
class StatusSnapshot:
    branch: str
    open_question_count: int = 0
    action_breakdown: ActionBreakdown = field(default_factory=ActionBreakdown)
    branches: list[BranchSummary] = field(default_factory=list)
    recent_decisions: list[Decision] = field(default_factory=list)
    latest_meeting: str | None = None
    incomplete_action_count: int = 0


def _classify_actions(actions: list[ActionItem], today: date) -> ActionBreakdown:
    breakdown = ActionBreakdown()
    week_end = today + timedelta(days=7)
    for a in actions:
        if a.status == "complete" or a.status == "cancelled":
            continue
        if a.due_date is None:
            breakdown.no_due_date += 1
        elif a.due_date < today:
            breakdown.overdue += 1
        elif a.due_date <= week_end:
            breakdown.due_this_week += 1
        else:
            breakdown.upcoming += 1
    return breakdown


def _branches_summary(repo: Repo) -> list[BranchSummary]:
    summary: list[BranchSummary] = []
    main_names = {"main", "master"}
    for head in repo.heads:
        if head.name in main_names:
            continue
        commit = head.commit
        ts = datetime.fromtimestamp(commit.committed_date, tz=UTC).date().isoformat()
        # If branch is "<id>/<rest>", surface the leading id as owner.
        owner = head.name.split("/", 1)[0] if "/" in head.name else None
        summary.append(BranchSummary(name=head.name, owner=owner, last_commit=ts))
    return summary


def _latest_meeting(paths: CairnPaths) -> str | None:
    if not paths.meetings.is_dir():
        return None
    dates: list[str] = []
    for child in paths.meetings.iterdir():
        m = MEETING_NAME.match(child.name)
        if m:
            dates.append(m.group(1))
    return max(dates) if dates else None


def _state_from_treeish(repo: Repo, branch: str) -> CairnState:
    """Read state files from ``branch`` without checking it out."""
    files = {
        "collaborators.yaml": Collaborator,
        "decisions.yaml": Decision,
        "open_questions.yaml": OpenQuestion,
        "action_items.yaml": ActionItem,
        "goals.yaml": Goal,
    }
    parsed: dict[str, list] = {}
    for name, model in files.items():
        try:
            text = repo.git.show(f"{branch}:state/{name}")
        except Exception:
            parsed[name] = []
            continue
        raw = yaml.safe_load(text) or []
        if not isinstance(raw, list):
            parsed[name] = []
            continue
        parsed[name] = TypeAdapter(list[model]).validate_python(raw)
    return CairnState(
        collaborators=parsed["collaborators.yaml"],
        decisions=parsed["decisions.yaml"],
        questions=parsed["open_questions.yaml"],
        actions=parsed["action_items.yaml"],
        goals=parsed["goals.yaml"],
    )


def build_status(
    paths: CairnPaths,
    state: CairnState,
    *,
    branch: str | None = None,
    today: date | None = None,
) -> StatusSnapshot:
    today = today or datetime.now(UTC).date()
    branch_name = branch or "main"
    repo = Repo(paths.root)

    snap = StatusSnapshot(branch=branch_name)
    open_qs = [q for q in state.questions if q.status == "open"]
    snap.open_question_count = len(open_qs)

    incomplete = [a for a in state.actions if a.status == "open"]
    snap.incomplete_action_count = len(incomplete)
    snap.action_breakdown = _classify_actions(state.actions, today)

    snap.branches = _branches_summary(repo)

    sorted_decisions = sorted(state.decisions, key=lambda d: d.date, reverse=True)
    snap.recent_decisions = sorted_decisions[:5]

    snap.latest_meeting = _latest_meeting(paths)
    return snap


def state_for_branch(paths: CairnPaths, branch: str | None) -> CairnState:
    """Return state for the named branch (defaults to current cwd's view)."""
    if branch is None:
        from ..io.state_io import load_state
        return load_state(paths)
    repo = Repo(paths.root)
    return _state_from_treeish(repo, branch)
