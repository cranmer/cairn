"""Regression tests for git identity resolution (git_ops.get_user_identity)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cairn import git_ops
from cairn.errors import NoUserIdentityError


@pytest.fixture
def no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip the env-var path so we exercise the repo/global fallback."""
    for var in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    ):
        monkeypatch.delenv(var, raising=False)


def test_get_user_identity_uses_global_git_config_when_env_unset(no_env):
    """Regression: Repo.config_reader('global') was wrongly called as a class method.

    The fix shells out to `git config --global ...` instead. With env vars stripped
    and no repo passed, get_user_identity must succeed when global config has values.
    """
    def fake_git_config(args, **kwargs):
        # args is ["git", "config", "--global", "user.name" | "user.email"]
        key = args[-1]
        if key == "user.name":
            stdout = "Globally Configured User\n"
        elif key == "user.email":
            stdout = "global@example.com\n"
        else:
            stdout = ""
        return _FakeCompleted(stdout=stdout, returncode=0)

    with patch.object(git_ops.subprocess, "run", side_effect=fake_git_config):
        ident = git_ops.get_user_identity(repo=None)

    assert ident.name == "Globally Configured User"
    assert ident.email == "global@example.com"


def test_get_user_identity_raises_when_nothing_configured(no_env):
    """No env, no repo, no global config → clear actionable error."""
    def empty_git_config(args, **kwargs):
        return _FakeCompleted(stdout="", returncode=1)

    with (
        patch.object(git_ops.subprocess, "run", side_effect=empty_git_config),
        pytest.raises(NoUserIdentityError) as exc,
    ):
        git_ops.get_user_identity(repo=None)

    assert "git config --global" in str(exc.value)


def test_get_user_identity_survives_missing_git_binary(no_env):
    """If `git` itself is not on PATH, the global lookup degrades gracefully."""
    def no_git(args, **kwargs):
        raise FileNotFoundError("git")

    with (
        patch.object(git_ops.subprocess, "run", side_effect=no_git),
        pytest.raises(NoUserIdentityError),
    ):
        git_ops.get_user_identity(repo=None)


class _FakeCompleted:
    def __init__(self, stdout: str, returncode: int):
        self.stdout = stdout
        self.returncode = returncode
