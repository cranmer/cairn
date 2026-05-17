"""Git operations: init, identity resolution, commit.

Uses GitPython, which shells out to the ``git`` binary already on PATH.
The substrate is git; this module is intentionally thin.
"""

from __future__ import annotations

import contextlib
import os
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


def _from_repo_or_global(repo: Repo | None) -> Identity | None:
    candidates = []
    if repo is not None:
        candidates.append(repo.config_reader())
    with contextlib.suppress(Exception):
        candidates.append(Repo.config_reader("global"))
    for reader in candidates:
        try:
            name = reader.get_value("user", "name")
            email = reader.get_value("user", "email")
        except Exception:
            continue
        if name and email:
            return Identity(name=str(name), email=str(email))
    return None


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
