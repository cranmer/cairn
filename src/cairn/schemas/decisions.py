"""Decision schema."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .common import CollaboratorId, EntityId, UtcDatetime

DecisionId = Annotated[str, StringConstraints(pattern=r"^D-\d{3,}$")]


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: DecisionId
    date: UtcDatetime
    author: CollaboratorId
    decision: str = Field(min_length=1)
    context: str | None = None
    supersedes: DecisionId | None = None
    superseded_by: DecisionId | None = None
    related: list[EntityId] = Field(default_factory=list)
    # Structured git provenance — optional. Useful when a decision was
    # extracted retroactively from PR/commit history; see ADR-0009
    # follow-up "Bootstrap & Retroactive Population".
    source_commits: list[str] = Field(default_factory=list)
    source_prs: list[str] = Field(default_factory=list)
