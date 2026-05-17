"""Render a StatusSnapshot for humans (text) and machines (JSON)."""

from __future__ import annotations

import json

from .snapshot import StatusSnapshot


def render_text(snap: StatusSnapshot) -> str:
    lines: list[str] = []
    lines.append(f"Cairn status [{snap.branch}]")
    lines.append("")
    lines.append(f"Open questions: {snap.open_question_count}")
    b = snap.action_breakdown
    lines.append(
        f"Incomplete actions: {snap.incomplete_action_count}  "
        f"(overdue {b.overdue}, this week {b.due_this_week}, "
        f"upcoming {b.upcoming}, no due date {b.no_due_date})"
    )
    if snap.branches:
        lines.append("")
        lines.append("Active branches:")
        for br in snap.branches:
            owner = f" ({br.owner})" if br.owner else ""
            lines.append(f"  - {br.name}{owner}, last {br.last_commit}")
    if snap.recent_decisions:
        lines.append("")
        lines.append("Recent decisions:")
        for d in snap.recent_decisions:
            date_str = d.date.date().isoformat()
            preview = d.decision if len(d.decision) <= 70 else d.decision[:67] + "..."
            lines.append(f"  - {d.id} ({date_str}) {preview}")
    if snap.latest_meeting:
        lines.append("")
        lines.append(f"Latest meeting: {snap.latest_meeting}")
    return "\n".join(lines)


def render_json(snap: StatusSnapshot) -> str:
    payload = {
        "branch": snap.branch,
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
        "latest_meeting": snap.latest_meeting,
    }
    return json.dumps(payload, indent=2)
