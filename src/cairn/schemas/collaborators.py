"""Collaborator schema (human and AI)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import CollaboratorId


class Collaborator(BaseModel):
    """A human or AI participant in a cairn.

    The same model covers both kinds, discriminated by ``type``. AI-only
    fields (``trigger``, ``scope``, ``permissions``) are free-form strings
    in Phase 0/1; structured permissions arrive with the AI-collaborator
    runtime later on.
    """

    model_config = ConfigDict(extra="forbid")

    id: CollaboratorId
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    type: Literal["human", "ai-collaborator"] = "human"
    email: str | None = None
    github: str | None = None
    expertise: list[str] = Field(default_factory=list)
    current_focus: str | None = None
    recent_papers: list[str] = Field(default_factory=list)
    notes: str | None = None

    trigger: str | None = None
    scope: str | None = None
    permissions: str | None = None
