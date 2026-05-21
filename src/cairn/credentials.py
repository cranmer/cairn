"""Credentials management for remote cairn endpoints.

Resolution order for bearer tokens (US-P-13):
1. ``CAIRN_BEARER_TOKEN`` environment variable
2. ``~/.config/cairn/credentials.toml``, keyed by endpoint URL

Credentials are never written into ``cairn.toml`` and never committed.
The credentials file is written with mode 0600 (user-read/write only).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from .errors import CairnError

CREDENTIALS_FILE = "credentials.toml"


class CredentialsError(CairnError):
    pass


def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "cairn"
    return Path.home() / ".config" / "cairn"


def credentials_path() -> Path:
    return _config_dir() / CREDENTIALS_FILE


def load_bearer_token(endpoint: str) -> str | None:
    """Load the bearer token for a remote endpoint.

    Returns None if no credentials are configured (not an error — unauthenticated
    servers don't require a token, and the caller decides whether to error).
    """
    env_token = os.environ.get("CAIRN_BEARER_TOKEN")
    if env_token:
        return env_token

    creds = credentials_path()
    if not creds.is_file():
        return None

    try:
        data = tomllib.loads(creds.read_text(encoding="utf-8"))
    except Exception:
        return None

    endpoints = data.get("endpoints", {})
    return endpoints.get(endpoint) or None


def save_bearer_token(endpoint: str, token: str) -> None:
    """Persist a bearer token for ``endpoint`` to ``~/.config/cairn/credentials.toml``.

    The file is created (or updated) with mode 0600 so only the owning user
    can read it.  Credentials are stored in a ``[endpoints]`` table keyed by
    the full endpoint URL string.
    """
    creds = credentials_path()
    creds.parent.mkdir(parents=True, exist_ok=True)

    existing_endpoints: dict[str, str] = {}
    if creds.is_file():
        try:
            data = tomllib.loads(creds.read_text(encoding="utf-8"))
            existing_endpoints = dict(data.get("endpoints", {}))
        except Exception:
            pass

    existing_endpoints[endpoint] = token

    lines = ["[endpoints]"]
    for url, tok in existing_endpoints.items():
        url_esc = url.replace("\\", "\\\\").replace('"', '\\"')
        tok_esc = tok.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'"{url_esc}" = "{tok_esc}"')
    lines.append("")

    creds.write_text("\n".join(lines), encoding="utf-8")
    creds.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
