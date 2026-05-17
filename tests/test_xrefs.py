"""Cross-reference resolution on CairnState."""

from __future__ import annotations

from cairn.schemas import CairnState, Collaborator, Decision, Goal, OpenQuestion


def _state() -> CairnState:
    return CairnState(
        collaborators=[
            Collaborator(id="kyle", name="Kyle", role="PI"),
            Collaborator(id="maria", name="Maria", role="postdoc"),
        ],
        decisions=[
            Decision(
                id="D-001",
                date="2026-05-01T00:00:00Z",
                author="kyle",
                decision="x",
            )
        ],
        questions=[
            OpenQuestion(
                id="Q-001",
                raised_by="maria",
                date="2026-05-02T00:00:00Z",
                question="?",
            )
        ],
        goals=[Goal(id="G-001", text="ship it", created="2026-05-03T00:00:00Z")],
    )


def test_collaborator_ids():
    assert _state().collaborator_ids() == {"kyle", "maria"}


def test_id_index_covers_all_entity_kinds():
    idx = _state().id_index()
    assert idx == {"D-001": "decision", "Q-001": "question", "G-001": "goal"}


def test_decision_ids_listed():
    assert _state().decision_ids() == ["D-001"]
