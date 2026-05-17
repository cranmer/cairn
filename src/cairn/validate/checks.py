"""Individual validation checks. Each returns a list of Issues."""

from __future__ import annotations

import re

import yaml
from pydantic import TypeAdapter, ValidationError

from ..paths import REQUIRED_DIRS, STATE_FILES, CairnPaths
from ..schemas import (
    ActionItem,
    CairnState,
    Collaborator,
    Decision,
    Goal,
    OpenQuestion,
)
from .report import Issue

MEETING_FILENAME = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def required_dirs_exist(paths: CairnPaths) -> list[Issue]:
    issues: list[Issue] = []
    for rel in REQUIRED_DIRS:
        target = paths.root / rel
        if not target.is_dir():
            issues.append(Issue(file=None, entity_id=None, message=f"missing directory: {rel}"))
    return issues


def yaml_parses(paths: CairnPaths) -> list[Issue]:
    issues: list[Issue] = []
    for name in STATE_FILES:
        f = paths.state / name
        if not f.is_file():
            issues.append(Issue(file=f, entity_id=None, message=f"missing state file: {name}"))
            continue
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            issues.append(Issue(file=f, entity_id=None, message=f"YAML parse error: {exc}"))
            continue
        if data is not None and not isinstance(data, list):
            issues.append(
                Issue(file=f, entity_id=None, message="expected top-level YAML list")
            )
    return issues


_SCHEMA_BY_FILE: dict[str, type] = {
    "decisions.yaml": Decision,
    "open_questions.yaml": OpenQuestion,
    "action_items.yaml": ActionItem,
    "goals.yaml": Goal,
    "collaborators.yaml": Collaborator,
}


def schemas_validate(paths: CairnPaths) -> list[Issue]:
    issues: list[Issue] = []
    for name, model in _SCHEMA_BY_FILE.items():
        f = paths.state / name
        if not f.is_file():
            continue
        try:
            raw = yaml.safe_load(f.read_text(encoding="utf-8")) or []
        except yaml.YAMLError:
            continue  # yaml_parses already reported
        if not isinstance(raw, list):
            continue
        adapter = TypeAdapter(list[model])
        try:
            adapter.validate_python(raw)
        except ValidationError as exc:
            for err in exc.errors():
                loc = err.get("loc", ())
                eid = None
                if loc and isinstance(loc[0], int) and 0 <= loc[0] < len(raw):
                    entry = raw[loc[0]] or {}
                    eid = entry.get("id") if isinstance(entry, dict) else None
                field_path = ".".join(str(p) for p in loc[1:]) or "<root>"
                issues.append(
                    Issue(
                        file=f,
                        entity_id=eid,
                        message=f"{field_path}: {err.get('msg', 'invalid')}",
                    )
                )
    return issues


def xrefs_resolve(state: CairnState, paths: CairnPaths) -> list[Issue]:
    issues: list[Issue] = []
    id_index = state.id_index()
    collaborator_ids = state.collaborator_ids()

    for d in state.decisions:
        if d.author not in collaborator_ids:
            issues.append(
                Issue(
                    file=paths.decisions_yaml,
                    entity_id=d.id,
                    message=f"author '{d.author}' is not a known collaborator",
                )
            )
        for ref in d.related:
            if ref not in id_index:
                issues.append(
                    Issue(
                        file=paths.decisions_yaml,
                        entity_id=d.id,
                        message=f"related id '{ref}' does not exist",
                    )
                )
        if d.supersedes and d.supersedes not in id_index:
            issues.append(
                Issue(
                    file=paths.decisions_yaml,
                    entity_id=d.id,
                    message=f"supersedes '{d.supersedes}' does not exist",
                )
            )

    for q in state.questions:
        if q.raised_by not in collaborator_ids:
            issues.append(
                Issue(
                    file=paths.open_questions_yaml,
                    entity_id=q.id,
                    message=f"raised_by '{q.raised_by}' is not a known collaborator",
                )
            )
        for ref in q.related:
            if ref not in id_index:
                issues.append(
                    Issue(
                        file=paths.open_questions_yaml,
                        entity_id=q.id,
                        message=f"related id '{ref}' does not exist",
                    )
                )

    for a in state.actions:
        if a.assignee not in collaborator_ids:
            issues.append(
                Issue(
                    file=paths.action_items_yaml,
                    entity_id=a.id,
                    message=f"assignee '{a.assignee}' is not a known collaborator",
                )
            )
        if a.completed_by and a.completed_by not in collaborator_ids:
            issues.append(
                Issue(
                    file=paths.action_items_yaml,
                    entity_id=a.id,
                    message=f"completed_by '{a.completed_by}' is not a known collaborator",
                )
            )
        for ref in a.related:
            if ref not in id_index:
                issues.append(
                    Issue(
                        file=paths.action_items_yaml,
                        entity_id=a.id,
                        message=f"related id '{ref}' does not exist",
                    )
                )

    for g in state.goals:
        for ref in g.related:
            if ref not in id_index:
                issues.append(
                    Issue(
                        file=paths.goals_yaml,
                        entity_id=g.id,
                        message=f"related id '{ref}' does not exist",
                    )
                )

    return issues


def meeting_filenames(paths: CairnPaths) -> list[Issue]:
    issues: list[Issue] = []
    meetings = paths.meetings
    if not meetings.is_dir():
        return issues
    for child in meetings.iterdir():
        if not child.is_file():
            continue
        if child.name == ".gitkeep":
            continue
        if child.suffix == ".md" and not MEETING_FILENAME.match(child.name):
            issues.append(
                Issue(
                    file=child,
                    entity_id=None,
                    message="meeting filenames must match YYYY-MM-DD.md",
                )
            )
    return issues


def strict_warnings(state: CairnState, paths: CairnPaths) -> list[Issue]:
    issues: list[Issue] = []
    referenced_by_decisions: set[str] = set()
    for d in state.decisions:
        referenced_by_decisions.update(d.related)

    for q in state.questions:
        if q.status == "open" and q.id not in referenced_by_decisions and not q.related:
            issues.append(
                Issue(
                    file=paths.open_questions_yaml,
                    entity_id=q.id,
                    message=(
                        "orphan open question (no related entries, "
                        "not referenced by any decision)"
                    ),
                    severity="warning",
                )
            )

    for d in state.decisions:
        if not d.author:  # impossible at schema level, but kept symmetrically
            issues.append(
                Issue(
                    file=paths.decisions_yaml,
                    entity_id=d.id,
                    message="decision missing author",
                    severity="warning",
                )
            )

    return issues
