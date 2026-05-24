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
    paired_via_http: bool = False  # scenario 2 uses HTTP cairn.toml


def _cairn_cmd() -> list[str]:
    """Invoke the cairn CLI via the running interpreter — keeps tests
    insulated from PATH and from whichever ``cairn`` binary happens to
    be installed."""
    return [sys.executable, "-m", "cairn"]


def _run(
    cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> None:
    subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
    )


def scaffold_fixture(
    name: str,
    dest_dir: Path,
    *,
    http_endpoint: str | None = None,
) -> tuple[Path, Path]:
    """Materialize a fixture project + paired cairn.

    Returns ``(project_dir, cairn_dir)``.

    ``dest_dir`` will contain:

    - ``<dest_dir>/projects/<name>/`` — the fictional project repo with
      ``cairn.toml`` pairing.
    - ``<dest_dir>/cairns/<name>/`` — the cairn itself.

    ``http_endpoint`` is only meaningful when the fixture has
    ``paired_via_http=True``; the resulting ``cairn.toml`` points at it.
    """
    from .fixtures_data import FIXTURES

    if name not in FIXTURES:
        raise KeyError(f"unknown fixture {name!r}; known: {sorted(FIXTURES)}")
    fix = FIXTURES[name]

    project_dir = dest_dir / "projects" / fix.name
    cairn_parent = dest_dir / "cairns"
    cairn_dir = cairn_parent / fix.name
    project_dir.mkdir(parents=True, exist_ok=True)
    cairn_parent.mkdir(parents=True, exist_ok=True)

    # 1. Write the project files.
    for f in fix.project_files:
        target = project_dir / f.relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(f.content))

    # 2. Init the cairn via `cairn init` so we exercise the same code path
    #    real users hit. `cairn init <name>` creates `<cwd>/<name>` — so
    #    we run it from the cairns/ parent.
    _run(_cairn_cmd() + ["init", fix.name, "--no-input"], cwd=cairn_parent)

    # 3. Write cairn.toml pairing (uses the [cairn] table per ADR-0012).
    if fix.paired_via_http:
        if not http_endpoint:
            raise ValueError(f"fixture {name!r} requires http_endpoint")
        cairn_toml = (
            "[cairn]\n"
            f'endpoint = "{http_endpoint}"\n'
            f'name = "{fix.name}"\n'
        )
    else:
        cairn_toml = f"[cairn]\nname = \"{fix.name}\"\n"
    (project_dir / "cairn.toml").write_text(cairn_toml)

    # 4. Git init + synthesized commits in the project dir.
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
                # Don't sign synthetic commits.
                "GIT_CONFIG_GLOBAL": "/dev/null",
            }
        )
        _run(
            ["git", "commit", "-q", "-m", commit.message],
            cwd=project_dir,
            env=env,
        )

    # 5. Seed cairn state via the CLI (so schemas validate by
    #    construction). cairn collaborator/decision/finding are scoped
    #    to a cairn root; we cd into cairn_dir for each.
    for c in fix.collaborators:
        cmd = _cairn_cmd() + [
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
        _run(cmd, cwd=cairn_dir)

    # Open questions don't have a CLI yet — write directly into
    # state/open_questions.yaml. The file is a top-level YAML list.
    # Tagged as a stopgap; once `cairn open-question add` lands,
    # collapse this into the same _run pattern as the others.
    if fix.questions:
        _seed_open_questions(cairn_dir, fix.questions)

    for d in fix.decisions:
        cmd = _cairn_cmd() + [
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
        _run(cmd, cwd=cairn_dir)

    for f in fix.findings:
        cmd = _cairn_cmd() + [
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
        _run(cmd, cwd=cairn_dir)

    return project_dir, cairn_dir


def _seed_open_questions(cairn_dir: Path, questions: list[FixtureQuestion]) -> None:
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
    _run(["git", "add", str(oq_file.relative_to(cairn_dir))], cwd=cairn_dir)
    _run(
        ["git", "commit", "-q", "-m", "Seed fixture open questions"],
        cwd=cairn_dir,
    )
