"""Path resolution for a cairn on disk."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import NotACairnError

# Marker file at the cairn root. See docs/decisions/0006-cairn-discovery-and-pairing.md.
MARKER_FILE = ".cairn"

# Pre-marker cairns predate ADR-0006 and identified themselves only by the
# presence of state/collaborators.yaml. Kept as a transitional fallback so
# in-the-wild cairns remain discoverable; `cairn validate` warns when the
# marker is missing so users can run the documented one-line backfill.
_LEGACY_MARKER = "state/collaborators.yaml"

STATE_FILES = (
    "decisions.yaml",
    "open_questions.yaml",
    "action_items.yaml",
    "goals.yaml",
    "collaborators.yaml",
)

REQUIRED_DIRS = (
    "state",
    "knowledge",
    "knowledge/meetings",
    "knowledge/findings",
    "knowledge/literature",
    "knowledge/provenance",
    "skills",
    "branches",
)


@dataclass(frozen=True)
class CairnPaths:
    """Resolved paths inside a cairn."""

    root: Path

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def knowledge(self) -> Path:
        return self.root / "knowledge"

    @property
    def meetings(self) -> Path:
        return self.knowledge / "meetings"

    @property
    def findings(self) -> Path:
        return self.knowledge / "findings"

    @property
    def literature(self) -> Path:
        return self.knowledge / "literature"

    @property
    def provenance(self) -> Path:
        return self.knowledge / "provenance"

    @property
    def skills(self) -> Path:
        return self.root / "skills"

    @property
    def branches(self) -> Path:
        return self.root / "branches"

    @property
    def project_md(self) -> Path:
        return self.root / "PROJECT.md"

    @property
    def collaborators_yaml(self) -> Path:
        return self.state / "collaborators.yaml"

    @property
    def decisions_yaml(self) -> Path:
        return self.state / "decisions.yaml"

    @property
    def open_questions_yaml(self) -> Path:
        return self.state / "open_questions.yaml"

    @property
    def action_items_yaml(self) -> Path:
        return self.state / "action_items.yaml"

    @property
    def goals_yaml(self) -> Path:
        return self.state / "goals.yaml"


def is_cairn_root(path: Path) -> bool:
    """A directory is a cairn root if it carries the ``.cairn`` marker.

    Falls back to the pre-marker convention (``state/collaborators.yaml``)
    so cairns scaffolded before ADR-0006 stay discoverable. The fallback
    will be removed once no pre-marker cairns remain in active use.
    """
    return (path / MARKER_FILE).is_file() or (path / _LEGACY_MARKER).is_file()


def has_marker(path: Path) -> bool:
    """True iff the cairn at ``path`` has the canonical ``.cairn`` marker."""
    return (path / MARKER_FILE).is_file()


def write_marker(root: Path, name: str) -> None:
    """Write the ``.cairn`` marker file at ``root``.

    Idempotent: if the marker already exists with the same name, it is left
    alone. Otherwise the file is (over)written with the canonical contents.
    """
    target = root / MARKER_FILE
    contents = (
        "# Cairn root marker — managed by `cairn init`. Do not edit by hand.\n"
        "# Presence of this file identifies the containing directory as a cairn root.\n"
        f'name = "{name}"\n'
    )
    if target.is_file() and target.read_text(encoding="utf-8") == contents:
        return
    target.write_text(contents, encoding="utf-8")


def find_cairn_root(start: Path) -> Path:
    """Walk upward from ``start`` looking for a cairn root."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if is_cairn_root(candidate):
            return candidate
    raise NotACairnError(f"no cairn found at or above {start}")


def resolve_cairn(start: Path | None = None) -> CairnPaths:
    """Resolve the cairn containing ``start`` (defaults to cwd)."""
    return CairnPaths(root=find_cairn_root(start or Path.cwd()))
