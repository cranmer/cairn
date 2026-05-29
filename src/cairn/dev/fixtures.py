"""Fixture project specs and scaffolder.

See ``tests/agent_smoke/multi-user-multi-cairn/fixtures/README.md`` for
the human-readable description of what each fixture represents. The
structured definitions live in :mod:`cairn.dev.fixtures_data`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml


@dataclass
class FixtureFile:
    relpath: str
    content: str


@dataclass
class FixtureCommit:
    author_name: str
    author_email: str
    message: str
    files: list[str]  # relpaths to add in this commit


@dataclass
class FixtureCollaborator:
    id: str
    name: str
    role: str
    type: str = "human"  # "human" | "unknown" | "ai-collaborator" | "group"
    email: str | None = None


@dataclass
class FixtureDecision:
    text: str  # the decision itself (1-2 sentences)
    author: str
    context: str | None = None
    related: list[str] = field(default_factory=list)


@dataclass
class FixtureQuestion:
    id: str  # e.g. "Q-001"
    question: str
    raised_by: str
    related: list[str] = field(default_factory=list)


@dataclass
class FixtureFinding:
    title: str
    author: str
    slug: str | None = None
    body: str | None = None
    related: list[str] = field(default_factory=list)


@dataclass
class Fixture:
    name: str  # the cairn name (also the project dir name)
    project_files: list[FixtureFile]
    commits: list[FixtureCommit]
    collaborators: list[FixtureCollaborator]
    decisions: list[FixtureDecision]
    questions: list[FixtureQuestion]
    findings: list[FixtureFinding]


def _cairn_cmd() -> list[str]:
    """Invoke the cairn CLI via the running interpreter — keeps tests
    insulated from PATH and from whichever ``cairn`` binary happens to
    be installed."""
    return [sys.executable, "-m", "cairn"]


def _dev_env() -> dict[str, str]:
    """Process env with synthetic git identity defaults filled in.

    Containerized dev MCP servers usually have no global git config; without
    this every `cairn init`, `cairn decision add`, etc. would fail at the
    initial commit with NoUserIdentityError. Real env values take precedence.
    """
    env = dict(os.environ)
    env.setdefault("GIT_AUTHOR_NAME", "Cairn Dev")
    env.setdefault("GIT_AUTHOR_EMAIL", "dev@cairn.local")
    env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
    env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])
    return env


def _run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True)
    if result.returncode != 0:
        detail = (
            result.stderr.decode(errors="replace").strip()
            or result.stdout.decode(errors="replace").strip()
            or "(no output)"
        )
        raise RuntimeError(
            f"{' '.join(cmd)} exited {result.returncode}: {detail}"
        )


def scaffold_project(
    name: str,
    project_dir: Path,
    *,
    http_endpoint: str | None = None,
    cairn_name: str | None = None,
) -> Path:
    """Materialize the project-repo half of a fixture.

    Writes project files, runs git init + the fixture's commit history,
    and writes ``cairn.toml`` pairing the repo with a cairn.

    - ``http_endpoint`` writes an HTTP-paired ``cairn.toml`` pointing at
      that URL; omit for a local-path-paired ``cairn.toml``.
    - ``cairn_name`` overrides the cairn handle stored in ``cairn.toml``
      (useful when the remote registered the cairn under a different
      handle than the fixture's local name). Defaults to ``name``.
    """
    from .fixtures_data import FIXTURES

    if name not in FIXTURES:
        raise KeyError(f"unknown fixture {name!r}; known: {sorted(FIXTURES)}")
    fix = FIXTURES[name]
    resolved_cairn_name = cairn_name or fix.name

    project_dir.mkdir(parents=True, exist_ok=True)

    for f in fix.project_files:
        target = project_dir / f.relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(f.content))

    if http_endpoint:
        cairn_toml = f'[cairn]\nendpoint = "{http_endpoint}"\nname = "{resolved_cairn_name}"\n'
    else:
        cairn_toml = f'[cairn]\nname = "{resolved_cairn_name}"\n'
    (project_dir / "cairn.toml").write_text(cairn_toml)

    _run(["git", "init", "-q", "-b", "main"], cwd=project_dir)
    for commit in fix.commits:
        for relpath in commit.files:
            _run(["git", "add", relpath], cwd=project_dir)
        env = dict(os.environ)
        env.update(
            {
                "GIT_AUTHOR_NAME": commit.author_name,
                "GIT_AUTHOR_EMAIL": commit.author_email,
                "GIT_COMMITTER_NAME": commit.author_name,
                "GIT_COMMITTER_EMAIL": commit.author_email,
                "GIT_CONFIG_GLOBAL": "/dev/null",
            }
        )
        _run(
            ["git", "commit", "-q", "-m", commit.message],
            cwd=project_dir,
            env=env,
        )
    return project_dir


def scaffold_cairn(
    name: str,
    cairn_dir: Path,
) -> dict:
    """Materialize the cairn half of a fixture.

    Runs ``cairn init`` at ``cairn_dir`` (which must not already exist)
    and seeds collaborators, decisions, open questions, and findings.
    Returns a summary dict suitable for client-side verification:

        {"fixture": name,
         "collaborators": [<ids>],
         "decisions": <int>,
         "questions": <int>,
         "findings": <int>}
    """
    from .fixtures_data import FIXTURES

    if name not in FIXTURES:
        raise KeyError(f"unknown fixture {name!r}; known: {sorted(FIXTURES)}")
    fix = FIXTURES[name]

    cairn_parent = cairn_dir.parent
    cairn_parent.mkdir(parents=True, exist_ok=True)
    # Inject a synthetic git identity so scaffolding works in containers
    # / CI where no global git config is set; `cairn init` and any later
    # git-touching cairn subcommand otherwise fail with NoUserIdentityError.
    dev_env = _dev_env()
    # `cairn init <name>` creates `<cwd>/<name>` — run it from the parent
    # and let the CLI pick the directory name.
    _run(
        [*_cairn_cmd(), "init", cairn_dir.name, "--no-input"],
        cwd=cairn_parent,
        env=dev_env,
    )

    for c in fix.collaborators:
        cmd = [
            *_cairn_cmd(),
            "collaborator",
            "add",
            "--id",
            c.id,
            "--name",
            c.name,
            "--role",
            c.role,
            "--type",
            c.type,
        ]
        if c.email:
            cmd.extend(["--email", c.email])
        _run(cmd, cwd=cairn_dir, env=dev_env)

    if fix.questions:
        _seed_open_questions(cairn_dir, fix.questions, env=dev_env)

    for d in fix.decisions:
        cmd = [
            *_cairn_cmd(),
            "decision",
            "add",
            "--author",
            d.author,
            "--text",
            d.text,
        ]
        if d.context:
            cmd.extend(["--context", d.context])
        for r in d.related:
            cmd.extend(["--related", r])
        _run(cmd, cwd=cairn_dir, env=dev_env)

    for f in fix.findings:
        cmd = [
            *_cairn_cmd(),
            "finding",
            "add",
            "--author",
            f.author,
            "--title",
            f.title,
        ]
        if f.slug:
            cmd.extend(["--slug", f.slug])
        if f.body:
            cmd.extend(["--body", f.body])
        for r in f.related:
            cmd.extend(["--related", r])
        _run(cmd, cwd=cairn_dir, env=dev_env)

    return {
        "fixture": name,
        "collaborators": [c.id for c in fix.collaborators],
        "decisions": len(fix.decisions),
        "questions": len(fix.questions),
        "findings": len(fix.findings),
    }


def scaffold_fixture(
    name: str,
    dest_dir: Path,
    *,
    http_endpoint: str | None = None,
) -> tuple[Path, Path]:
    """Materialize a fixture project + paired cairn on the local machine.

    Returns ``(project_dir, cairn_dir)``. Produces:

    - ``<dest_dir>/projects/<name>/`` — fictional project repo with
      ``cairn.toml`` pairing.
    - ``<dest_dir>/cairns/<name>/`` — the cairn itself.

    ``http_endpoint`` makes ``cairn.toml`` an HTTP-paired one pointing at
    that URL; omit for a local-path-paired ``cairn.toml``. Either way,
    the cairn is also scaffolded locally — for a truly-remote setup
    where the cairn lives on the server, use ``scaffold_project`` alone
    and let the server materialize the cairn via its MCP tool.
    """
    from .fixtures_data import FIXTURES

    if name not in FIXTURES:
        raise KeyError(f"unknown fixture {name!r}; known: {sorted(FIXTURES)}")

    project_dir = dest_dir / "projects" / name
    cairn_dir = dest_dir / "cairns" / name
    scaffold_project(name, project_dir, http_endpoint=http_endpoint)
    scaffold_cairn(name, cairn_dir)
    return project_dir, cairn_dir


def _seed_open_questions(
    cairn_dir: Path,
    questions: list[FixtureQuestion],
    *,
    env: dict[str, str] | None = None,
) -> None:
    """Direct file write — no CLI for open questions exists yet."""
    oq_file = cairn_dir / "state" / "open_questions.yaml"
    existing = yaml.safe_load(oq_file.read_text()) or []
    if not isinstance(existing, list):
        existing = []
    now = datetime.now(timezone.utc).replace(microsecond=0)
    iso = now.isoformat().replace("+00:00", "Z")
    for q in questions:
        existing.append(
            {
                "id": q.id,
                "raised_by": q.raised_by,
                "date": iso,
                "question": q.question,
                "status": "open",
                "related": list(q.related),
            }
        )
    oq_file.write_text(yaml.safe_dump(existing, sort_keys=False))
    # Stage + commit so the cairn stays in a clean state for downstream
    # commands.
    _run(["git", "add", str(oq_file.relative_to(cairn_dir))], cwd=cairn_dir, env=env)
    _run(
        ["git", "commit", "-q", "-m", "Seed fixture open questions"],
        cwd=cairn_dir,
        env=env,
    )
