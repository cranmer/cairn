"""Project-repo ``cairn.toml`` pointer file (Stage 2 / ADR-0006 + ADR-0010).

A project repo paired with a cairn carries a ``cairn.toml`` at its root.
Three valid modes:

    [cairn]
    path = "../stellaforge-cairn"   # local-path: filesystem path relative to cairn.toml

    [cairn]
    name = "stellaforge"            # local-registry: name in ~/.config/cairn/server.toml

    [cairn]
    endpoint = "https://cairn.example.com"   # remote MCP: HTTP MCP server
    name = "stellaforge"                     # cairn handle on that server (required)

Invalid combinations (rejected with an actionable error): empty pointer;
both ``name`` and ``path``; both ``endpoint`` and ``path``; ``endpoint``
without ``name``.
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
    """Parsed contents of a project-repo's ``cairn.toml`` pointer file.

    Exactly one of three modes is active (inspectable via the ``mode`` property):
    - ``"local-path"``: ``path`` is set; ``name`` and ``endpoint`` are None.
    - ``"local-registry"``: ``name`` is set; ``path`` and ``endpoint`` are None.
    - ``"remote"``: both ``endpoint`` and ``name`` are set; ``path`` is None.
    """

    name: str | None
    path: Path | None
    endpoint: str | None
    source: Path  # absolute path to the cairn.toml that produced this pointer

    @property
    def project_repo_root(self) -> Path:
        """The project repo's root (the directory containing the cairn.toml)."""
        return self.source.parent

    @property
    def mode(self) -> str:
        """One of ``"local-path"``, ``"local-registry"``, or ``"remote"``."""
        if self.path is not None:
            return "local-path"
        if self.endpoint is not None:
            return "remote"
        return "local-registry"

    @property
    def is_remote(self) -> bool:
        return self.mode == "remote"


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

    # Validate mode: three valid combinations, four invalid ones.
    has_name = name is not None
    has_path = raw_path is not None
    has_endpoint = endpoint is not None

    if not has_name and not has_path and not has_endpoint:
        raise CairnTomlError(
            f"{path}: [cairn] table must specify a pointer. "
            f"Use `path` (local path), `name` (registered cairn), "
            f"or `endpoint` + `name` (remote MCP server)."
        )
    if has_path and has_name:
        raise CairnTomlError(
            f"{path}: [cairn] specifies both `path` and `name` — use exactly one. "
            f"For a remote server use `endpoint` + `name` (no `path`)."
        )
    if has_path and has_endpoint:
        raise CairnTomlError(
            f"{path}: [cairn] specifies both `path` and `endpoint` — "
            f"local-path and remote modes are mutually exclusive."
        )
    if has_endpoint and not has_name:
        raise CairnTomlError(
            f"{path}: [cairn].endpoint requires [cairn].name (the cairn handle "
            f"on the remote server). Add `name = \"<cairn-handle>\"` to the "
            f"[cairn] section."
        )
    if has_name and has_path and has_endpoint:
        raise CairnTomlError(
            f"{path}: [cairn] specifies all three of `name`, `path`, and "
            f"`endpoint` — only one mode is allowed."
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

    Valid combinations:
    - ``name`` only → local-registry mode
    - ``path`` only → local-path mode
    - ``endpoint`` + ``name`` → remote MCP mode

    Returns the absolute path to the written file.
    """
    has_name = name is not None
    has_path = path is not None
    has_endpoint = endpoint is not None

    if not has_name and not has_path and not has_endpoint:
        raise CairnTomlError("write_pointer requires at least one of name/path/endpoint")
    if has_path and has_name and not has_endpoint:
        raise CairnTomlError("write_pointer: name and path are mutually exclusive")
    if has_path and has_endpoint:
        raise CairnTomlError("write_pointer: path and endpoint are mutually exclusive")
    if has_endpoint and not has_name:
        raise CairnTomlError("write_pointer: endpoint requires name (the cairn handle on the server)")
    if has_name and has_path and has_endpoint:
        raise CairnTomlError("write_pointer: specify only one mode (name, path, or endpoint+name)")

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
    if has_endpoint:
        # Remote MCP mode: endpoint + name
        assert name is not None
        endpoint_esc = endpoint.replace("\\", "\\\\").replace('"', '\\"')  # type: ignore[union-attr]
        name_esc = name.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'endpoint = "{endpoint_esc}"')
        lines.append(f'name = "{name_esc}"')
    elif has_name:
        assert name is not None
        name_esc = name.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'name = "{name_esc}"')
    else:
        assert path is not None
        # Prefer a path relative to the project repo when possible, for portability.
        try:
            rel = path.resolve().relative_to(project_repo.resolve())
            path_str = str(rel)
        except ValueError:
            # Try walking up — express as ../sibling-dir if they share a parent.
            try:
                pr_parts = project_repo.resolve().parts
                pa_parts = path.resolve().parts
                common_len = 0
                for a, b in zip(pr_parts, pa_parts, strict=False):
                    if a == b:
                        common_len += 1
                    else:
                        break
                if common_len > 0:
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

    lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
