"""YAML load / dump helpers.

Reads go through pyyaml (fast, simple). Writes go through ruamel.yaml so
that comments and key ordering humans have added by hand survive round
trips. The state files are intended to be human-editable; preserving
their incidental structure matters.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import yaml
from ruamel.yaml import YAML

_writer = YAML()
_writer.preserve_quotes = True
# Top-level sequences start at column 0 (sequence=2, offset=0). The previous
# (4, 2) settings produced a leading two-space indent on top-level list items,
# which is legal YAML but unusual and causes diff noise on hand-edits.
_writer.indent(mapping=2, sequence=2, offset=0)
_writer.width = 100


def _represent_none(representer, _data):  # ruamel signature
    """Render Python ``None`` as the explicit token ``null`` rather than blank.

    Without this, an optional unset field renders as ``key:`` which is legal
    YAML but visually identical to "this key has no body" and easy to misread.
    ``key: null`` is unambiguous.
    """
    return representer.represent_scalar("tag:yaml.org,2002:null", "null")


_writer.representer.add_representer(type(None), _represent_none)


def load_yaml(path: Path) -> list[dict[str, Any]]:
    """Load a YAML file expected to contain a top-level list.

    An empty file or a file containing only ``[]`` returns an empty list.
    Returns the empty list (rather than ``None``) for compatibility with
    the schema-load helpers.
    """
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected top-level YAML list, got {type(data).__name__}")
    return data


def dump_yaml(path: Path, items: list[dict[str, Any]]) -> None:
    """Write ``items`` to ``path`` as a YAML list.

    Atomic: writes to a sibling temp file and renames into place.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    if items:
        _writer.dump(items, buf)
    else:
        buf.write("[]\n")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8")
    tmp.replace(path)
