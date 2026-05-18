"""Read/write markdown files that carry YAML frontmatter.

Format:

    ---
    key: value
    other: thing
    ---
    Body markdown goes here.

No external dependency — pyyaml is already pulled in for state files, and
the parser is simple enough to do by hand.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DELIMITER = "---"


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body) from a markdown-with-frontmatter string.

    Raises ``ValueError`` if the file has no frontmatter block or it is
    malformed.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != DELIMITER:
        raise ValueError("missing leading '---' frontmatter delimiter")
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == DELIMITER:
            end = i
            break
    if end is None:
        raise ValueError("missing closing '---' frontmatter delimiter")
    fm_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1:])
    if body and not body.endswith("\n"):
        body += "\n"
    data = yaml.safe_load(fm_text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"frontmatter must be a YAML mapping, got {type(data).__name__}")
    return data, body


def load(path: Path) -> tuple[dict[str, Any], str]:
    """Read ``path`` and return (frontmatter, body)."""
    return parse(path.read_text(encoding="utf-8"))


def dump(frontmatter: dict[str, Any], body: str) -> str:
    """Render a markdown-with-frontmatter string. Body trailing newline normalized."""
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False).rstrip()
    body_text = body.rstrip("\n")
    return f"{DELIMITER}\n{fm_text}\n{DELIMITER}\n{body_text}\n" if body_text else (
        f"{DELIMITER}\n{fm_text}\n{DELIMITER}\n"
    )


def write(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    """Atomically write a markdown-with-frontmatter file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(dump(frontmatter, body), encoding="utf-8")
    tmp.replace(path)
