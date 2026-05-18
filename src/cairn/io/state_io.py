"""Load and write the five canonical state files as schema objects."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError

from ..errors import SchemaError
from ..paths import CairnPaths
from ..schemas import (
    ActionItem,
    CairnState,
    Collaborator,
    Decision,
    Goal,
    OpenQuestion,
)
from .yaml_io import dump_yaml, load_yaml

M = TypeVar("M", bound=BaseModel)


def _load_list(path, model: type[M]) -> list[M]:
    raw = load_yaml(path)
    adapter = TypeAdapter(list[model])
    try:
        return adapter.validate_python(raw)
    except ValidationError as exc:
        raise SchemaError(f"{path}: {exc}") from exc


_AI_ONLY_COLLABORATOR_FIELDS = frozenset({"trigger", "scope", "permissions"})


def _serialize(model: BaseModel) -> dict[str, Any]:
    """Render a state model as a YAML-ready dict.

    Substrate-as-truth: keep optional fields visible (``exclude_none=False``)
    so the schema is documented by example in the file itself, rather than
    quietly dropping fields the user might want to know about.

    Exception: on a human ``Collaborator``, drop the AI-collaborator-only
    fields (``trigger``, ``scope``, ``permissions``) — emitting them as
    ``null`` on humans is misleading rather than informative.
    """
    data: dict[str, Any] = model.model_dump(mode="json", exclude_none=False)
    if isinstance(model, Collaborator) and data.get("type") != "ai-collaborator":
        for f in _AI_ONLY_COLLABORATOR_FIELDS:
            data.pop(f, None)
    return data


def _dump_list(path, items: list[BaseModel]) -> None:
    serialized = [_serialize(m) for m in items]
    dump_yaml(path, serialized)


def load_collaborators(paths: CairnPaths) -> list[Collaborator]:
    return _load_list(paths.collaborators_yaml, Collaborator)


def load_decisions(paths: CairnPaths) -> list[Decision]:
    return _load_list(paths.decisions_yaml, Decision)


def load_questions(paths: CairnPaths) -> list[OpenQuestion]:
    return _load_list(paths.open_questions_yaml, OpenQuestion)


def load_actions(paths: CairnPaths) -> list[ActionItem]:
    return _load_list(paths.action_items_yaml, ActionItem)


def load_goals(paths: CairnPaths) -> list[Goal]:
    return _load_list(paths.goals_yaml, Goal)


def load_state(paths: CairnPaths) -> CairnState:
    return CairnState(
        collaborators=load_collaborators(paths),
        decisions=load_decisions(paths),
        questions=load_questions(paths),
        actions=load_actions(paths),
        goals=load_goals(paths),
    )


def write_collaborators(paths: CairnPaths, items: list[Collaborator]) -> None:
    _dump_list(paths.collaborators_yaml, items)


def write_decisions(paths: CairnPaths, items: list[Decision]) -> None:
    _dump_list(paths.decisions_yaml, items)


def write_questions(paths: CairnPaths, items: list[OpenQuestion]) -> None:
    _dump_list(paths.open_questions_yaml, items)


def write_actions(paths: CairnPaths, items: list[ActionItem]) -> None:
    _dump_list(paths.action_items_yaml, items)


def write_goals(paths: CairnPaths, items: list[Goal]) -> None:
    _dump_list(paths.goals_yaml, items)
