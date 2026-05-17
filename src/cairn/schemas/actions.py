"""Action item schema."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .common import CollaboratorId, EntityId, UtcDatetime

ActionId = Annotated[str, StringConstraints(pattern=r"^A-\d{3,}$")]


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: ActionId
    assignee: CollaboratorId
    text: str = Field(min_length=1)
    created: UtcDatetime
    due_date: date | None = None
    status: Literal["open", "complete", "cancelled"] = "open"
    completed_at: UtcDatetime | None = None
    completed_by: CollaboratorId | None = None
    related: list[EntityId] = Field(default_factory=list)

    @model_validator(mode="after")
    def _completion_fields_consistent(self) -> ActionItem:
        if self.status == "complete" and (
            self.completed_at is None or self.completed_by is None
        ):
            raise ValueError(
                "completed action items require both completed_at and completed_by"
            )
        return self
