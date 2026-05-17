"""Schema validation tests."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from cairn.schemas import (
    ActionItem,
    Collaborator,
    Decision,
    Goal,
    OpenQuestion,
)


def test_collaborator_minimum_fields():
    c = Collaborator(id="maria", name="Maria Santos", role="postdoc")
    assert c.type == "human"
    assert c.expertise == []


def test_collaborator_ai_variant():
    c = Collaborator(
        id="lit-monitor",
        name="Literature Monitor",
        role="literature monitor",
        type="ai-collaborator",
        trigger="weekly",
        scope="arxiv stat.ML",
        permissions="write to lit-monitor/* only",
    )
    assert c.type == "ai-collaborator"
    assert c.trigger == "weekly"


def test_collaborator_id_must_be_kebab_lowercase():
    with pytest.raises(ValidationError):
        Collaborator(id="Maria", name="x", role="x")
    with pytest.raises(ValidationError):
        Collaborator(id="maria santos", name="x", role="x")


def test_collaborator_rejects_unknown_field():
    with pytest.raises(ValidationError):
        Collaborator(id="maria", name="x", role="x", title="oops")


def test_decision_roundtrip_utc():
    d = Decision(
        id="D-014",
        date="2026-04-22T15:30:00Z",
        author="kyle",
        decision="Use stratified resampling",
        context="Discussed in meeting",
        related=["Q-007"],
    )
    assert d.date == datetime(2026, 4, 22, 15, 30, tzinfo=UTC)
    dumped = d.model_dump(mode="json")
    assert dumped["date"] == "2026-04-22T15:30:00Z"


def test_decision_naive_datetime_assumed_utc():
    d = Decision(
        id="D-001",
        date=datetime(2026, 5, 1, 12, 0),
        author="kyle",
        decision="x",
    )
    assert d.date.tzinfo is UTC


def test_decision_id_pattern():
    with pytest.raises(ValidationError):
        Decision(id="D-1", date="2026-01-01T00:00:00Z", author="x", decision="x")


def test_open_question_defaults():
    q = OpenQuestion(
        id="Q-012",
        raised_by="maria",
        date="2026-05-08T00:00:00Z",
        question="Does the bias correction introduce identifiability problems",
    )
    assert q.status == "open"
    assert q.related == []


def test_action_item_complete_requires_completion_fields():
    with pytest.raises(ValidationError):
        ActionItem(
            id="A-001",
            assignee="kyle",
            text="ship it",
            created="2026-05-01T00:00:00Z",
            status="complete",
        )


def test_action_item_complete_ok_with_completion_fields():
    a = ActionItem(
        id="A-001",
        assignee="kyle",
        text="ship it",
        created="2026-05-01T00:00:00Z",
        status="complete",
        completed_at="2026-05-08T00:00:00Z",
        completed_by="kyle",
    )
    assert a.due_date is None


def test_action_item_due_date_is_calendar_date():
    a = ActionItem(
        id="A-002",
        assignee="kyle",
        text="ship it",
        created="2026-05-01T00:00:00Z",
        due_date=date(2026, 5, 15),
    )
    assert a.due_date == date(2026, 5, 15)


def test_goal_minimum():
    g = Goal(id="G-001", text="ship Cairn v1", created="2026-05-01T00:00:00Z")
    assert g.status == "active"
