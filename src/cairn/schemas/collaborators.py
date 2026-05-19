"""Collaborator schema (human and AI)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import CollaboratorId


class Collaborator(BaseModel):
    """A human, AI, or virtual participant in a cairn.

    The same model covers all kinds, discriminated by ``type``:

    - ``human`` (default) — a person, attributed via git authorship.
    - ``ai-collaborator`` — a configured AI agent with its own identity
      (literature monitor, critique agent, etc.).
    - ``virtual`` — a placeholder identity for observations that don't
      have a single authoring human or AI. Useful for retroactive
      bootstrap attribution (e.g., ``id="repo-history"`` for findings
      extracted from a repo's docs / TODO markers / commit history)
      and for representing consensus / group / meeting-derived
      authorship until proper multi-author or meeting-linkage schema
      lands (see ``docs/open-questions.md``).

    AI-only fields (``trigger``, ``scope``, ``permissions``) are
    free-form strings in Phase 0/1; structured permissions arrive
    with the AI-collaborator runtime later on.
    """

    model_config = ConfigDict(extra="forbid")

    id: CollaboratorId
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    type: Literal["human", "ai-collaborator", "virtual"] = "human"
    email: str | None = None
    github: str | None = None
    expertise: list[str] = Field(default_factory=list)
    current_focus: str | None = None
    recent_papers: list[str] = Field(default_factory=list)
    notes: str | None = None

    trigger: str | None = None
    scope: str | None = None
    permissions: str | None = None
