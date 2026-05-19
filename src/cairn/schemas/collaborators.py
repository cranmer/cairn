"""Collaborator schema (human and AI)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import CollaboratorId


class Collaborator(BaseModel):
    """A human, AI, group, or unknown participant in a cairn.

    The same model covers all kinds, discriminated by ``type``:

    - ``human`` (default) — a person, attributed via git authorship.
    - ``ai-collaborator`` — a configured AI agent with its own identity
      (literature monitor, critique agent, etc.).
    - ``group`` — a named multi-person aggregate ("consensus",
      "core-team", "methods-team"). Used when authorship is genuinely
      shared and no single human is the primary author. A stopgap
      until proper multi-author schema lands (see ADR-0011 /
      ``docs/decisions/0011-multi-author-attribution.md`` and OQ-5 in
      ``docs/open-questions.md``).
    - ``unknown`` — an explicit "we don't know who authored this"
      placeholder, used by the ``bootstrap_from_repo`` skill for
      observations derived from a project's docs / TODO markers /
      commit history where no single authoring human is plausible.
      The canonical id for the bootstrap case is ``repo-history``.

    AI-only fields (``trigger``, ``scope``, ``permissions``) are
    free-form strings in Phase 0/1; structured permissions arrive
    with the AI-collaborator runtime later on.
    """

    model_config = ConfigDict(extra="forbid")

    id: CollaboratorId
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    type: Literal["human", "ai-collaborator", "group", "unknown"] = "human"
    email: str | None = None
    github: str | None = None
    expertise: list[str] = Field(default_factory=list)
    current_focus: str | None = None
    recent_papers: list[str] = Field(default_factory=list)
    notes: str | None = None

    trigger: str | None = None
    scope: str | None = None
    permissions: str | None = None
