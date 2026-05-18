"""Regression tests for git identity resolution (git_ops.get_user_identity)
and for the commit-signing escape hatch (git_ops.disable_signing_if_unable_to_sign).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
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


# ---------------------------------------------------------------------------
# disable_signing_if_unable_to_sign
# ---------------------------------------------------------------------------


def _fake_repo(tmp_path: Path) -> SimpleNamespace:
    """Minimal stand-in for git.Repo — only working_dir is read."""
    return SimpleNamespace(working_dir=str(tmp_path))


def _config_router(values: dict[str, str]):
    """Build a subprocess.run side-effect that answers `git -C ... config --get K`."""
    writes: list[list[str]] = []

    def side_effect(args, **kwargs):
        # Writes (no --get flag) are recorded and reported as success.
        if "--get" not in args:
            writes.append(list(args))
            return _FakeCompleted(stdout="", returncode=0)
        key = args[-1]
        if key in values:
            return _FakeCompleted(stdout=values[key] + "\n", returncode=0)
        return _FakeCompleted(stdout="", returncode=1)

    return side_effect, writes


def test_disable_signing_no_op_when_user_has_signing_key(tmp_path):
    """User opted into signing — leave their config alone."""
    side_effect, writes = _config_router(
        {"user.signingkey": "ABC123", "commit.gpgsign": "true"}
    )
    with patch.object(git_ops.subprocess, "run", side_effect=side_effect):
        wrote = git_ops.disable_signing_if_unable_to_sign(_fake_repo(tmp_path))
    assert wrote is False
    assert writes == []


def test_disable_signing_writes_override_when_gpgsign_on_without_key(tmp_path):
    """The trap case the smoke test surfaced: gpgsign=true, no key → override."""
    side_effect, writes = _config_router({"commit.gpgsign": "true"})
    with patch.object(git_ops.subprocess, "run", side_effect=side_effect):
        wrote = git_ops.disable_signing_if_unable_to_sign(_fake_repo(tmp_path))
    assert wrote is True
    # Exactly one write, targeting the new repo's local config.
    assert len(writes) == 1
    assert writes[0] == [
        "git", "-C", str(tmp_path), "config", "commit.gpgsign", "false"
    ]


def test_disable_signing_no_op_when_gpgsign_unset(tmp_path):
    """No global signing-on preference → nothing to fix."""
    side_effect, writes = _config_router({})
    with patch.object(git_ops.subprocess, "run", side_effect=side_effect):
        wrote = git_ops.disable_signing_if_unable_to_sign(_fake_repo(tmp_path))
    assert wrote is False
    assert writes == []


def test_disable_signing_no_op_when_gpgsign_explicitly_false(tmp_path):
    """User has gpgsign=false globally → also no fix needed."""
    side_effect, writes = _config_router({"commit.gpgsign": "false"})
    with patch.object(git_ops.subprocess, "run", side_effect=side_effect):
        wrote = git_ops.disable_signing_if_unable_to_sign(_fake_repo(tmp_path))
    assert wrote is False
    assert writes == []


def test_disable_signing_survives_missing_git_binary(tmp_path):
    """If `git` isn't on PATH, degrade silently rather than crashing init."""
    def no_git(args, **kwargs):
        raise FileNotFoundError("git")

    with patch.object(git_ops.subprocess, "run", side_effect=no_git):
        wrote = git_ops.disable_signing_if_unable_to_sign(_fake_repo(tmp_path))
    assert wrote is False
