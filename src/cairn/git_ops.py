"""Git operations: init, identity resolution, commit.

Uses GitPython, which shells out to the ``git`` binary already on PATH.
The substrate is git; this module is intentionally thin.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from git import Actor, Repo

from .errors import NoUserIdentityError


@dataclass(frozen=True)
class Identity:
    name: str
    email: str

    @property
    def actor(self) -> Actor:
        return Actor(self.name, self.email)


def init_repo(path: Path) -> Repo:
    """Initialize ``path`` as a new git repository."""
    return Repo.init(path, mkdir=False)


def _from_env() -> Identity | None:
    name = os.environ.get("GIT_AUTHOR_NAME") or os.environ.get("GIT_COMMITTER_NAME")
    email = os.environ.get("GIT_AUTHOR_EMAIL") or os.environ.get("GIT_COMMITTER_EMAIL")
    if name and email:
        return Identity(name=name, email=email)
    return None


def _git_config_value(scope: str, key: str) -> str | None:
    """Read a value by shelling out to ``git config <scope> <key>``.

    ``scope`` is e.g. ``"--global"`` or ``"--system"``. Returns ``None`` if
    ``git`` is missing, the lookup times out, or the key is unset.
    """
    try:
        result = subprocess.run(
            ["git", "config", scope, key],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _from_repo(repo: Repo) -> Identity | None:
    """Read identity from the repo's config reader (includes inherited global/system)."""
    with contextlib.suppress(Exception):
        reader = repo.config_reader()
        name = reader.get_value("user", "name", default=None)
        email = reader.get_value("user", "email", default=None)
        if name and email:
            return Identity(name=str(name), email=str(email))
    return None


def _git_config_in_repo(repo_path: Path, key: str) -> str | None:
    """Read the effective value of ``key`` as seen from inside ``repo_path``.

    Unlike :func:`_git_config_value` (which targets a single scope), this returns
    the value combining system/global/local/env scopes — i.e. what git itself
    would use when running a command inside the repo.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "config", "--get", key],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def disable_signing_if_unable_to_sign(repo: Repo) -> bool:
    """Write repo-local ``commit.gpgsign=false`` if signing would otherwise fail.

    The CLI creates commits via GitPython's Python-level index API, which
    bypasses ``commit.gpgsign`` entirely. The user's *subsequent* manual
    ``git commit`` invocations inside the cairn do not — and on hosts where
    ``commit.gpgsign=true`` is set globally without a configured signing key,
    those manual commits fail with an opaque signing error.

    If the user has ``user.signingkey`` configured anywhere, this is a no-op
    (they intentionally opted into signing). Otherwise, if signing would be
    enabled by default, write a repo-local override so future manual commits
    in this cairn just work.

    Returns ``True`` iff the override was written.
    """
    repo_path = Path(repo.working_dir)
    if _git_config_in_repo(repo_path, "user.signingkey"):
        return False
    gpgsign = _git_config_in_repo(repo_path, "commit.gpgsign")
    if gpgsign is None or gpgsign.lower() != "true":
        return False
    try:
        subprocess.run(
            ["git", "-C", str(repo_path), "config", "commit.gpgsign", "false"],
            check=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False
    return True


def _from_global() -> Identity | None:
    """Read identity from ``git config --global`` without needing a repo."""
    name = _git_config_value("--global", "user.name")
    email = _git_config_value("--global", "user.email")
    if name and email:
        return Identity(name=name, email=email)
    return None


def _from_repo_or_global(repo: Repo | None) -> Identity | None:
    if repo is not None:
        ident = _from_repo(repo)
        if ident is not None:
            return ident
    return _from_global()


def get_user_identity(repo: Repo | None = None) -> Identity:
    """Resolve the invoking user's git identity.

    Lookup order: ``GIT_AUTHOR_*`` env vars, then the repo-level git
    config, then the global git config. Raises ``NoUserIdentityError``
    with actionable instructions if no identity is configured.
    """
    ident = _from_env() or _from_repo_or_global(repo)
    if ident is None:
        raise NoUserIdentityError(
            "no git user identity configured. "
            "Run `git config --global user.name 'Your Name'` "
            "and `git config --global user.email 'you@example.com'`."
        )
    return ident


def commit(
    repo: Repo,
    paths: list[Path],
    message: str,
    *,
    author: Identity | None = None,
) -> str:
    """Stage the given files (only) and create a commit. Returns SHA."""
    author = author or get_user_identity(repo)
    rels = [str(p.resolve().relative_to(Path(repo.working_dir).resolve())) for p in paths]
    repo.index.add(rels)
    commit_obj = repo.index.commit(message, author=author.actor, committer=author.actor)
    return commit_obj.hexsha
