"""US-P-01 — Initialize a new cairn (default template)."""

from __future__ import annotations

from pathlib import Path

from git import Repo
from typer.testing import CliRunner

from cairn.cli.app import app
from cairn.io.state_io import load_state
from cairn.paths import CairnPaths

runner = CliRunner()


def _invoke_init(cwd: Path, name: str = "test-project", *extra: str):
    return runner.invoke(
        app,
        ["init", name, *extra],
        catch_exceptions=False,
    )


def test_us_p_01_creates_full_directory_tree(cwd: Path):
    result = _invoke_init(cwd)
    assert result.exit_code == 0, result.output
    root = cwd / "test-project"
    for sub in (
        "state",
        "knowledge/meetings",
        "knowledge/findings",
        "knowledge/literature",
        "knowledge/provenance",
        "skills",
        "branches",
    ):
        assert (root / sub).is_dir(), f"missing {sub}"
    for f in ("README.md", "PROJECT.md", ".gitignore"):
        assert (root / f).is_file(), f"missing {f}"


def test_us_p_01_state_files_exist_and_are_schema_valid(cwd: Path):
    _invoke_init(cwd)
    paths = CairnPaths(root=cwd / "test-project")
    for name in (
        "decisions.yaml",
        "open_questions.yaml",
        "action_items.yaml",
        "goals.yaml",
        "collaborators.yaml",
    ):
        assert (paths.state / name).is_file()
    # Schema-valid (and empty) load:
    state = load_state(paths)
    assert state.collaborators == []
    assert state.decisions == []
    assert state.questions == []
    assert state.actions == []
    assert state.goals == []


def test_us_p_01_bundles_skill_files(cwd: Path):
    """Phase 1 skills ship into newly-scaffolded cairns."""
    _invoke_init(cwd)
    skills_dir = cwd / "test-project" / "skills"
    expected = {
        "orient",
        "search-history",
        "start-branch",
        "complete-action",
        "log-finding",
        "resolve-branch",
        "debrief",
    }
    present = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    assert expected <= present, f"missing skills: {expected - present}"
    for name in expected:
        skill_md = skills_dir / name / "SKILL.md"
        assert skill_md.is_file(), f"{name}/SKILL.md missing"
        text = skill_md.read_text()
        assert text.startswith("---\n"), f"{name}/SKILL.md must start with YAML frontmatter"
        assert f"name: {name}" in text


def test_us_p_01_bundles_tracking_stance_guide(cwd: Path):
    """Every new cairn ships TRACKING.md so the agent has a posture guide."""
    _invoke_init(cwd)
    tracking = cwd / "test-project" / "TRACKING.md"
    assert tracking.is_file()
    text = tracking.read_text()
    # Sanity: the guide should mention the capture-eagerly posture and signals table.
    assert "capture eagerly" in text.lower()
    assert "signals to listen for" in text.lower()


def test_us_p_01_bundles_claude_session_start_hook(cwd: Path):
    """The cairn template ships a Claude Code SessionStart hook."""
    import json

    _invoke_init(cwd)
    settings = cwd / "test-project" / ".claude" / "settings.json"
    assert settings.is_file(), "missing .claude/settings.json"
    data = json.loads(settings.read_text())
    session_start = data.get("hooks", {}).get("SessionStart")
    assert session_start, "SessionStart hook missing from settings.json"
    # The hook should invoke `cairn status` (with a graceful fallback if not on PATH).
    serialized = json.dumps(data)
    assert "cairn status" in serialized
    # Per-user companion file must be gitignored:
    gitignore = (cwd / "test-project" / ".gitignore").read_text()
    assert ".claude/settings.local.json" in gitignore


def test_us_p_01_initial_commit_excludes_dot_git_internals(cwd: Path):
    """Regression: the initial commit must not stage .git/ files."""
    _invoke_init(cwd)
    repo = Repo(cwd / "test-project")
    tracked = repo.git.ls_tree("-r", "--name-only", "HEAD").splitlines()
    leaked = [p for p in tracked if p.startswith(".git/")]
    assert not leaked, f"initial commit leaked .git/ paths: {leaked[:5]}"


def test_us_p_01_project_md_interpolates_name_and_keeps_todos(cwd: Path):
    _invoke_init(cwd, "alpha-study")
    text = (cwd / "alpha-study" / "PROJECT.md").read_text()
    assert "# alpha-study" in text
    assert "TODO" in text


def test_us_p_01_initial_commit_attributed_to_user(cwd: Path):
    _invoke_init(cwd)
    repo = Repo(cwd / "test-project")
    commits = list(repo.iter_commits())
    assert len(commits) == 1
    assert commits[0].author.name == "Test User"
    assert commits[0].author.email == "test@example.com"
    assert "scaffold cairn 'test-project'" in commits[0].message


def test_us_p_01_refuses_overwrite_without_force(cwd: Path):
    first = _invoke_init(cwd)
    assert first.exit_code == 0
    second = _invoke_init(cwd)
    assert second.exit_code != 0
    assert "refusing to overwrite" in second.output.lower() or "exists" in second.output.lower()


def test_us_p_01_force_overwrites(cwd: Path):
    _invoke_init(cwd)
    # leave a marker, then re-init with --force
    (cwd / "test-project" / "PROJECT.md").write_text("MUTATED")
    result = _invoke_init(cwd, "test-project", "--force")
    assert result.exit_code == 0, result.output
    text = (cwd / "test-project" / "PROJECT.md").read_text()
    assert text != "MUTATED"
    assert "# test-project" in text
