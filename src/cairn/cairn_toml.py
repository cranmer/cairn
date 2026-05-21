"""Project-repo `cairn.toml` pointer file (ADR-0006 + ADR-0010 + ADR-0012).

A project repo paired with a cairn carries a `cairn.toml` at its root.
Three modes (per ADR-0012):

  local-path      path = "../stellaforge-cairn"
  local-registry  name = "stellaforge"
  remote-mcp      endpoint = "https://mcp.example.com/mcp"
                  name = "stellaforge"   # cairn handle on the remote server

``path`` alone → local-path mode (filesystem path, relative to the cairn.toml).
``name`` alone → local-registry mode (resolves via ~/.config/cairn/server.toml).
``endpoint + name`` → remote-MCP mode (HTTP MCP server; name is the cairn handle).

Invalid combinations (rejected with an actionable error):
- empty (none of the above)
- ``path + name``, ``path + endpoint``, or all three
- ``endpoint`` without ``name``
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

    Mode is determined by which fields are set:
    - local-path:     path set, name/endpoint None
    - local-registry: name set, path/endpoint None
    - remote-mcp:     endpoint + name both set, path None
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
    def is_remote(self) -> bool:
        """True when this pointer is in remote-MCP mode (endpoint + name)."""
        return self.endpoint is not None and self.name is not None


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

    # Validate the mode combination.
    # Valid: path alone | name alone | endpoint+name together.
    # Invalid: empty; path+name; path+endpoint; endpoint alone; all three.
    if raw_path is not None and (name is not None or endpoint is not None):
        raise CairnTomlError(
            f"{path}: [cairn].path cannot be combined with `name` or `endpoint`. "
            f"Use `name` for local-registry mode, or `endpoint + name` for remote-MCP mode."
        )
    if endpoint is not None and name is None:
        raise CairnTomlError(
            f"{path}: [cairn].endpoint requires `name` (the cairn handle on the remote server). "
            f"Add `name = \"<handle>\"` to the [cairn] table."
        )
    if raw_path is None and name is None and endpoint is None:
        raise CairnTomlError(
            f"{path}: [cairn] table must specify one of: "
            f"`path` (local-path), `name` (local-registry), "
            f"or `endpoint + name` (remote-MCP)."
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
    - ``path`` alone → local-path mode
    - ``name`` alone → local-registry mode
    - ``endpoint + name`` → remote-MCP mode

    Returns the absolute path to the written file.
    """
    # Validate the combination.
    if path is not None and (name is not None or endpoint is not None):
        raise CairnTomlError("write_pointer: path cannot be combined with name or endpoint")
    if endpoint is not None and name is None:
        raise CairnTomlError(
            "write_pointer: endpoint requires name (cairn handle on the remote server)"
        )
    if path is None and name is None and endpoint is None:
        raise CairnTomlError("write_pointer requires one of: path, name, or endpoint+name")

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
    if path is not None:
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
    elif endpoint is not None:
        # remote-MCP mode: endpoint + name
        assert name is not None
        endpoint_esc = endpoint.replace("\\", "\\\\").replace('"', '\\"')
        name_esc = name.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'endpoint = "{endpoint_esc}"')
        lines.append(f'name = "{name_esc}"')
    else:
        # local-registry mode: name only
        assert name is not None
        name_esc = name.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'name = "{name_esc}"')

    lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
