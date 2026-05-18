"""Shared types and helpers for Cairn schemas."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer, StringConstraints

COLLABORATOR_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,30}$"
ENTITY_ID_PATTERN = r"^[A-Z]-\d{3,}$"


CollaboratorId = Annotated[str, StringConstraints(pattern=COLLABORATOR_ID_PATTERN)]
EntityId = Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)]


def _ensure_utc(value: datetime | str) -> datetime:
    """Coerce timestamp input to a timezone-aware timezone.utc ``datetime``."""
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _serialize_utc(value: datetime) -> str:
    """Serialize a datetime as RFC 3339 with ``Z`` suffix."""
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    aware = aware.astimezone(timezone.utc)
    text = aware.isoformat(timespec="seconds")
    if text.endswith("+00:00"):
        text = text[:-6] + "Z"
    return text


UtcDatetime = Annotated[
    datetime,
    BeforeValidator(_ensure_utc),
    PlainSerializer(_serialize_utc, return_type=str),
]


ID_REGEX = re.compile(ENTITY_ID_PATTERN)
