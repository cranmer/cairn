"""Finding schema — YAML frontmatter of files under ``knowledge/findings/``.

A finding is a markdown file at ``knowledge/findings/YYYY-MM-DD-<slug>.md``.
The file's path is its canonical identity (there are no ``F-NNN`` IDs);
the schema below validates the YAML frontmatter the file carries.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .common import CollaboratorId, EntityId, UtcDatetime

FindingSlug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,60}$")]


class FindingFrontmatter(BaseModel):
    """YAML frontmatter for a finding file."""

    model_config = ConfigDict(extra="forbid")

    date: UtcDatetime
    author: CollaboratorId
    title: str = Field(min_length=1)
    slug: FindingSlug
    related: list[EntityId] = Field(default_factory=list)
    exploration: str | None = None
    # Structured git provenance — optional. Useful for retroactive
    # bootstrap from a project repo's history.
    source_commits: list[str] = Field(default_factory=list)
    source_prs: list[str] = Field(default_factory=list)


FINDING_FILENAME = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>[a-z0-9][a-z0-9-]*)\.md$")
