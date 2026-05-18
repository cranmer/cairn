"""US-A-02 — Log a finding mid-session (and `cairn finding add` coverage)."""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Repo
from typer.testing import CliRunner

from cairn.cli.app import app
from cairn.io import frontmatter as fm

runner = CliRunner()


def _bootstrap(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    runner.invoke(app, ["init", "p", "--no-input"], catch_exceptions=False)
    root = cwd / "p"
    monkeypatch.chdir(root)
    runner.invoke(app, ["collaborator", "add", "--id", "kyle", "--name", "K", "--role", "PI"])
    return root


def test_us_a_02_writes_file_with_frontmatter(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        [
            "finding", "add",
            "--author", "kyle",
            "--title", "Stratified resampling beats SMOTE",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    files = list((root / "knowledge" / "findings").glob("*.md"))
    assert len(files) == 1
    data, body = fm.load(files[0])
    assert data["author"] == "kyle"
    assert data["title"] == "Stratified resampling beats SMOTE"
    assert data["slug"] == "stratified-resampling-beats-smote"
    assert "TODO" in body


def test_us_a_02_filename_uses_date_and_slug(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    from datetime import datetime, timezone

    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(
        app,
        ["finding", "add", "--author", "kyle", "--title", "X Y Z"],
        catch_exceptions=False,
    )
    today = datetime.now(timezone.utc).date().isoformat()
    expected = root / "knowledge" / "findings" / f"{today}-x-y-z.md"
    assert expected.is_file()


def test_us_a_02_author_must_be_known(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        ["finding", "add", "--author", "ghost", "--title", "x"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "ghost" in res.output


def test_us_a_02_related_must_resolve(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    _bootstrap(cwd, monkeypatch)
    res = runner.invoke(
        app,
        ["finding", "add", "--author", "kyle", "--title", "x", "--related", "Q-999"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "Q-999" in res.output


def test_us_a_02_related_resolved_ok(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["decision", "add", "--author", "kyle", "--text", "decided"])
    res = runner.invoke(
        app,
        [
            "finding", "add",
            "--author", "kyle",
            "--title", "Linked",
            "--related", "D-001",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    f = next((root / "knowledge" / "findings").glob("*.md"))
    data, _ = fm.load(f)
    assert data["related"] == ["D-001"]


def test_us_a_02_branch_recorded_in_frontmatter(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["branch", "start", "explore"], catch_exceptions=False)
    runner.invoke(
        app,
        ["finding", "add", "--author", "kyle", "--title", "Found on branch"],
        catch_exceptions=False,
    )
    f = next((root / "knowledge" / "findings").glob("*.md"))
    data, _ = fm.load(f)
    assert data["branch"] == "kyle/explore"


def test_us_a_02_commits_attributed_to_user(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(
        app,
        ["finding", "add", "--author", "kyle", "--title", "Logged"],
        catch_exceptions=False,
    )
    head = next(Repo(root).iter_commits())
    assert "Log finding" in head.message
    assert head.author.email == "test@example.com"


def test_us_a_02_no_commit_skips_commit(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    root = _bootstrap(cwd, monkeypatch)
    repo = Repo(root)
    before = repo.head.commit.hexsha
    res = runner.invoke(
        app,
        [
            "finding", "add",
            "--author", "kyle",
            "--title", "Drafted",
            "--no-commit",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    assert repo.head.commit.hexsha == before  # no new commit
    files = list((root / "knowledge" / "findings").glob("*.md"))
    assert len(files) == 1


def test_us_a_02_duplicate_slug_same_day_errors(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    _bootstrap(cwd, monkeypatch)
    runner.invoke(app, ["finding", "add", "--author", "kyle", "--title", "Same Topic"])
    res = runner.invoke(
        app,
        ["finding", "add", "--author", "kyle", "--title", "Same Topic"],
        catch_exceptions=False,
    )
    assert res.exit_code != 0
    assert "already exists" in res.output.lower()


def test_us_a_02_explicit_slug_overrides_title(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(
        app,
        [
            "finding", "add",
            "--author", "kyle",
            "--title", "Some long descriptive title",
            "--slug", "short-name",
        ],
        catch_exceptions=False,
    )
    f = next((root / "knowledge" / "findings").glob("*.md"))
    assert f.name.endswith("-short-name.md")


def test_us_a_02_body_from_file(cwd: Path, monkeypatch: pytest.MonkeyPatch, tmp_path_factory):
    root = _bootstrap(cwd, monkeypatch)
    body_src = tmp_path_factory.mktemp("body") / "body.md"
    body_src.write_text("## Result\n\nWe saw a 5x lift.\n")
    runner.invoke(
        app,
        [
            "finding", "add",
            "--author", "kyle",
            "--title", "Lift",
            "--body-from", str(body_src),
        ],
        catch_exceptions=False,
    )
    f = next((root / "knowledge" / "findings").glob("*.md"))
    _, body = fm.load(f)
    assert "5x lift" in body


def test_us_a_02_body_and_body_from_mutually_exclusive(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, tmp_path_factory
):
    _bootstrap(cwd, monkeypatch)
    body_src = tmp_path_factory.mktemp("body") / "body.md"
    body_src.write_text("x")
    res = runner.invoke(
        app,
        [
            "finding", "add",
            "--author", "kyle",
            "--title", "x",
            "--body", "inline",
            "--body-from", str(body_src),
        ],
        catch_exceptions=False,
    )
    assert res.exit_code != 0


def test_us_a_02_validate_catches_bad_finding(cwd: Path, monkeypatch: pytest.MonkeyPatch):
    """`cairn validate` reports findings with broken frontmatter / bad refs."""
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(
        app, ["finding", "add", "--author", "kyle", "--title", "Sound finding"]
    )
    # Finding whose frontmatter is schema-valid but whose cross-references are not.
    bad = root / "knowledge" / "findings" / "2026-05-17-broken.md"
    bad.write_text(
        "---\n"
        "date: '2026-05-17T00:00:00Z'\n"
        "author: ghost\n"
        "title: broken\n"
        "slug: broken\n"
        "related: [Q-999]\n"
        "---\n"
        "body\n"
    )
    res = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "ghost" in res.output
    assert "Q-999" in res.output


def test_us_a_02_validate_catches_filename_mismatch(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
):
    root = _bootstrap(cwd, monkeypatch)
    runner.invoke(
        app, ["finding", "add", "--author", "kyle", "--title", "Sound finding"]
    )
    # Wrong filename format:
    bad = root / "knowledge" / "findings" / "no-date.md"
    bad.write_text("---\nfoo: bar\n---\nbody\n")
    res = runner.invoke(app, ["validate"], catch_exceptions=False)
    assert res.exit_code != 0
    assert "YYYY-MM-DD" in res.output
