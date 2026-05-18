"""Render a StatusSnapshot for humans (text) and machines (JSON)."""

from __future__ import annotations

import json

from .snapshot import StatusSnapshot


def _ids_preview(ids: list[str], max_inline: int = 3) -> str:
    """Format a list of ids for inline display: '(kyle)' or '(kyle, maria, +2)'."""
    if not ids:
        return ""
    if len(ids) <= max_inline:
        return " (" + ", ".join(ids) + ")"
    head = ", ".join(ids[:max_inline])
    return f" ({head}, +{len(ids) - max_inline})"


def render_text(snap: StatusSnapshot) -> str:
    lines: list[str] = []

    # Header: project name + cairn root.
    if snap.cairn_root:
        lines.append(f"Cairn '{snap.project_name}' [{snap.cairn_root}]")
    else:
        lines.append(f"Cairn '{snap.project_name}'")

    # Counts.
    lines.append(
        f"  Collaborators: {snap.collaborator_count}"
        f"{_ids_preview(snap.collaborator_ids)}"
    )
    lines.append(
        f"  Goals: {snap.goal_count}    "
        f"Decisions: {snap.decision_count}    "
        f"Open questions: {snap.open_question_count}    "
        f"Findings: {snap.finding_count}"
    )
    b = snap.action_breakdown
    lines.append(
        f"  Actions: {snap.incomplete_action_count} incomplete "
        f"(overdue {b.overdue}, this week {b.due_this_week}, "
        f"upcoming {b.upcoming}, no due date {b.no_due_date})"
    )

    # Git state.
    if snap.git_branch is not None or snap.last_commit_sha is not None:
        gb = snap.git_branch or "(detached)"
        if snap.last_commit_sha and snap.last_commit_message:
            msg = snap.last_commit_message
            if len(msg) > 60:
                msg = msg[:57] + "..."
            lines.append(f"  Git: {gb} @ {snap.last_commit_sha} — \"{msg}\"")
        else:
            lines.append(f"  Git: {gb}")

    # Active exploration branches (excluding main/master).
    if snap.branches:
        names = ", ".join(br.name for br in snap.branches)
        lines.append(f"  Active branches: {names}")
    else:
        lines.append("  Active branches: none")

    if snap.recent_decisions:
        lines.append("")
        lines.append("Recent decisions:")
        for d in snap.recent_decisions:
            date_str = d.date.date().isoformat()
            preview = d.decision if len(d.decision) <= 70 else d.decision[:67] + "..."
            lines.append(f"  - {d.id} ({date_str}) {preview}")

    if snap.recent_findings:
        lines.append("")
        lines.append(f"Findings ({snap.finding_count} total, most recent):")
        for f in snap.recent_findings:
            title = f.title or "(no title)"
            preview = title if len(title) <= 70 else title[:67] + "..."
            lines.append(f"  - {f.date} {preview}")

    if snap.latest_meeting:
        lines.append("")
        lines.append(f"Latest meeting: {snap.latest_meeting}")

    return "\n".join(lines)


def render_json(snap: StatusSnapshot) -> str:
    payload = {
        "project_name": snap.project_name,
        "cairn_root": snap.cairn_root,
        "branch": snap.branch,
        "git_branch": snap.git_branch,
        "last_commit_sha": snap.last_commit_sha,
        "last_commit_message": snap.last_commit_message,
        "collaborator_count": snap.collaborator_count,
        "collaborator_ids": snap.collaborator_ids,
        "goal_count": snap.goal_count,
        "decision_count": snap.decision_count,
        "open_question_count": snap.open_question_count,
        "incomplete_action_count": snap.incomplete_action_count,
        "action_breakdown": {
            "overdue": snap.action_breakdown.overdue,
            "due_this_week": snap.action_breakdown.due_this_week,
            "upcoming": snap.action_breakdown.upcoming,
            "no_due_date": snap.action_breakdown.no_due_date,
        },
        "branches": [
            {"name": br.name, "owner": br.owner, "last_commit": br.last_commit}
            for br in snap.branches
        ],
        "recent_decisions": [
            {
                "id": d.id,
                "date": d.date.isoformat().replace("+00:00", "Z"),
                "author": d.author,
                "decision": d.decision,
            }
            for d in snap.recent_decisions
        ],
        "finding_count": snap.finding_count,
        "recent_findings": [
            {"path": f.path, "date": f.date, "title": f.title}
            for f in snap.recent_findings
        ],
        "latest_meeting": snap.latest_meeting,
    }
    return json.dumps(payload, indent=2)
