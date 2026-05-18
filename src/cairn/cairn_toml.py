"""Project-repo `cairn.toml` pointer file (Stage 2 / ADR-0006 + ADR-0010).

A project repo paired with a cairn carries a `cairn.toml` at its root:

    [cairn]
    name = "stellaforge"           # registered name (preferred)
    # path = "../stellaforge-cairn"  # OR a local path (fallback)
    # endpoint = "stdio:cairn mcp"   # OR an MCP endpoint URL (future)

Exactly one of ``name``, ``path``, or ``endpoint`` is required. ``name`` is
the canonical form going forward (resolves against the user's MCP registry);
``path`` is a useful fallback when the user hasn't set up an MCP server.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from .errors import CairnError

POINTER_FILE = "cairn.toml"


class CairnTomlError(CairnError):
    pass


@dataclass(frozen=True)
class CairnPointer:
    """Parsed contents of a project-repo's ``cairn.toml`` pointer file."""

    name: str | None
    path: Path | None
    endpoint: str | None
    source: Path  # absolute path to the cairn.toml that produced this pointer

    @property
    def project_repo_root(self) -> Path:
        """The project repo's root (the directory containing the cairn.toml)."""
        return self.source.parent


def find_pointer(start: Path) -> Path | None:
    """Walk upward from ``start`` looking for a ``cairn.toml`` pointer file.

    Returns the absolute path to the first match, or None if none is found.
    """
    start = start.resolve()
    for candidate in (start, *start.parents):
        target = candidate / POINTER_FILE
        if target.is_file():
            return target
    return None


def load_pointer(path: Path) -> CairnPointer:
    """Parse a cairn.toml file. Raises CairnTomlError on schema problems."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise CairnTomlError(f"{path}: invalid TOML: {exc}") from None

    section = data.get("cairn")
    if not isinstance(section, dict):
        raise CairnTomlError(f"{path}: missing required [cairn] table")

    name = section.get("name")
    raw_path = section.get("path")
    endpoint = section.get("endpoint")

    if name is not None and not isinstance(name, str):
        raise CairnTomlError(f"{path}: [cairn].name must be a string")
    if raw_path is not None and not isinstance(raw_path, str):
        raise CairnTomlError(f"{path}: [cairn].path must be a string")
    if endpoint is not None and not isinstance(endpoint, str):
        raise CairnTomlError(f"{path}: [cairn].endpoint must be a string")

    present = sum(1 for v in (name, raw_path, endpoint) if v is not None)
    if present == 0:
        raise CairnTomlError(
            f"{path}: [cairn] table must specify exactly one of "
            f"`name`, `path`, or `endpoint`"
        )
    if present > 1:
        raise CairnTomlError(
            f"{path}: [cairn] table must specify exactly one of "
            f"`name`, `path`, or `endpoint` (found {present})"
        )

    resolved_path: Path | None = None
    if raw_path is not None:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = (path.parent / candidate).resolve()
        else:
            candidate = candidate.resolve()
        resolved_path = candidate

    return CairnPointer(
        name=name,
        path=resolved_path,
        endpoint=endpoint,
        source=path,
    )


def write_pointer(
    project_repo: Path,
    *,
    name: str | None = None,
    path: Path | None = None,
    endpoint: str | None = None,
) -> Path:
    """Write a ``cairn.toml`` at ``project_repo``'s root.

    Exactly one of name/path/endpoint must be provided. Returns the
    absolute path to the written file.
    """
    present = sum(1 for v in (name, path, endpoint) if v is not None)
    if present != 1:
        raise CairnTomlError(
            "write_pointer requires exactly one of name/path/endpoint"
        )

    if not project_repo.is_dir():
        raise CairnTomlError(f"project repo path is not a directory: {project_repo}")

    target = project_repo / POINTER_FILE
    lines = [
        "# Cairn pointer — managed by `cairn link`.",
        "# Identifies which cairn this project repo pairs with so agents can "
        "discover it from cwd.",
        "",
        "[cairn]",
    ]
    if name is not None:
        lines.append(f'name = "{name}"')
    elif path is not None:
        # Prefer a path relative to the project repo when possible, for portability.
        try:
            rel = path.resolve().relative_to(project_repo.resolve())
            path_str = str(rel)
        except ValueError:
            # Try walking up — express as ../sibling-dir if they share a parent.
            try:
                common = Path(
                    *(
                        p
                        for p in path.resolve().parts
                        if p in project_repo.resolve().parts
                    )
                )
                if str(common) and common != Path():
                    # Compute a ../-style relative path.
                    pr_parts = project_repo.resolve().parts
                    pa_parts = path.resolve().parts
                    common_len = 0
                    for a, b in zip(pr_parts, pa_parts, strict=False):
                        if a == b:
                            common_len += 1
                        else:
                            break
                    ups = ["..."] * (len(pr_parts) - common_len)
                    ups = [".."] * (len(pr_parts) - common_len)
                    downs = list(pa_parts[common_len:])
                    path_str = "/".join(ups + downs)
                else:
                    path_str = str(path.resolve())
            except Exception:
                path_str = str(path.resolve())
        # TOML basic-string escaping
        path_str = path_str.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'path = "{path_str}"')
    else:
        assert endpoint is not None
        endpoint_esc = endpoint.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'endpoint = "{endpoint_esc}"')

    lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
