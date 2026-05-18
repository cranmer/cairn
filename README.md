# Cairn

> A tool and design standard for hybrid human/AI research collaboration.

Cairn defines a repository structure, file schemas, and conventions for maintaining a research group's shared project memory — designed for a world where AI agents contribute alongside humans. The substrate is a git repository; everything else (agents, indices, dashboards, MCP servers) is a layer on top that can be added or replaced without compromising the source of truth.

**Two terms to know:**

- **Cairn** (capitalized) is the framework — this repo, the Python package, the conventions.
- **a cairn** (lowercase) is an instance — one research project's repository organized following Cairn's conventions. A research group runs one cairn per project.

> **Status:** Phase 0/1 implemented. The Python package scaffolds new cairns, manages collaborators and decisions, validates state, and reports project status. See [QUICKSTART.md](QUICKSTART.md) for a five-minute tour. For the full vision, see [the design overview](docs/overview.html).

## What it enables

- **Persistent shared memory** across meetings, decisions, findings, and discussions.
- **Async contribution and recall** — collaborators (and their agents) can ask what was decided, what was discussed, and what's outstanding without sitting through the original conversation.
- **Parallel exploration** via git branches, with explicit merge proposals as a deliberate social step.
- **Uniform interface for human and AI collaborators** — same workflows, attributed identities.
- **Reproducible artifact export** into emerging community standards (ASTRA, ARA, RO-Crate).

## Documentation

| Document | Purpose |
|----------|---------|
| [QUICKSTART.md](QUICKSTART.md) | Five-minute install + first cairn (human-driven) |
| [AGENT-BOOTSTRAP.md](AGENT-BOOTSTRAP.md) | Paste-into-Claude-Code instructions for agent-driven setup |
| [docs/overview.html](docs/overview.html) | Polished overview for sharing with colleagues |
| [docs/splash.html](docs/splash.html) | Single-page introduction |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Design document — principles, components, build path |
| [USER_STORIES.md](USER_STORIES.md) | Specifications for the Python package, agent skills, and MCP server |
| [CLAUDE.md](CLAUDE.md) | Development guide for Claude Code sessions |
| [docs/decisions/](docs/decisions/) | Architectural decision records (ADRs) |

## Repository contents

```
cairn/
├── README.md
├── QUICKSTART.md                  # install + first cairn in five minutes
├── ARCHITECTURE.md                # design document
├── USER_STORIES.md                # testable specifications (US-P-NN, US-A-NN, US-M-NN)
├── CLAUDE.md                      # development guide for Claude Code
├── pyproject.toml                 # hatchling build, deps, ruff + pytest config
├── figures/                       # architecture diagrams (SVG)
├── docs/
│   ├── overview.html              # polished overview
│   ├── splash.html                # single-page introduction
│   └── decisions/                 # ADRs (YAML library, git library, etc.)
├── templates/
│   └── default/                   # canonical cairn template (cookiecutter layout)
│       └── {{cookiecutter.project_name}}/
│           └── skills/            # bundled SKILL.md files (orient, search-history, …)
├── src/cairn/                     # Python package source
│   ├── schemas/                   # Pydantic v2 models for the five state files
│   ├── io/                        # YAML load/dump + state-file I/O
│   ├── template/                  # Jinja2 renderer for `cairn init` templates
│   ├── validate/                  # checks, runner, report for `cairn validate`
│   ├── status/                    # snapshot + renderers for `cairn status`
│   ├── cli/                       # Typer subcommands (init, collaborator, decision, …)
│   ├── git_ops.py                 # init/commit/identity helpers
│   ├── paths.py                   # cairn-root resolution + canonical paths
│   ├── ids.py                     # entity ID parse + next-ID generator
│   └── errors.py                  # exception hierarchy
└── tests/                         # pytest tests, one file per US-P-NN
```

## Roadmap

- [x] Design and architecture documented
- [x] User stories defined
- [x] **Phase 0 — Foundation** *(done)*
  - Canonical cairn template (`templates/default/`)
  - State schemas in Pydantic v2 (`src/cairn/schemas/`)
  - `cairn init` (US-P-01, US-P-02)
  - Basic state operations: `cairn collaborator add`, `cairn decision add`, `cairn validate`, `cairn status` (US-P-03 through US-P-06)
- [x] **Phase 1 — Agent skills + supporting commands** *(done)*
  - Bundled `SKILL.md` files in `templates/default/skills/`: `orient`, `search-history`, `start-branch`, `resolve-branch`, `complete-action`, `log-finding`
  - US-A-01: Orient at session start (reads `PROJECT.md` + `state/collaborators.yaml`, runs `cairn status`)
  - US-A-03: Create an exploration branch (`cairn branch start`)
  - US-A-04: Mark an action item complete (`cairn action add` + `cairn action complete`)
  - US-A-05: Search prior discussions (skill — local file scan)
  - US-A-09: Close an exploration branch (`cairn branch close`, merged or abandoned)
- [ ] **Phase 2 — Python package extensions** *(in progress)*
  - [x] Log a finding mid-session — `cairn finding add` + `log-finding` skill (US-A-02)
  - [ ] Meeting import (US-P-07)
  - [ ] Artifact export — ASTRA / ARA / RO-Crate (US-P-08)
  - [ ] Agenda draft (US-P-09)
- [ ] **Phase 3** — MCP server alongside the repo
- [ ] **Phase 4** — Meeting capture (Whisper + pyannote diarization)
- [ ] **Phase 5** — AI collaborator runtime (literature monitor, etc.)
- [ ] **Phase 6** — Voice-mode meeting participant *(long-term)*

## Available commands

Once installed (`pip install -e ".[dev]"`):

| Command | Purpose |
|---------|---------|
| `cairn init <name>` | Scaffold a new cairn from the bundled template or `--template <path-or-url>` |
| `cairn collaborator add` | Register a human or AI collaborator (flags or `--yaml` bulk) |
| `cairn decision add` | Record a decision with auto ID, UTC timestamp, and cross-reference validation |
| `cairn action add` | Add an action item with assignee, optional due date, and related-ID validation |
| `cairn action complete <id>` | Mark an action complete; records completion time and completer (keeps history) |
| `cairn branch start "<desc>"` | Create `<user-id>/<kebab>` branch + manifest, update `branches/README.md` |
| `cairn branch close <name>` | Record a branch as merged or abandoned; updates manifest + branches/README.md |
| `cairn finding add` | Write `knowledge/findings/YYYY-MM-DD-<slug>.md` with YAML frontmatter and commit it |
| `cairn validate` | Check schemas, cross-references, and meeting filenames; non-zero exit on errors |
| `cairn status` | Compact summary of open questions, actions, branches, recent decisions; supports `--json` and `--branch` |
| `cairn version` | Print the package version |

## Development

This repo is being developed with [Claude Code](https://claude.com/claude-code). When you open it in Claude Code, the agent reads `CLAUDE.md` automatically — it provides orientation, conventions, and the current phase's priorities.

**Stack:**
- Python 3.10+
- Environment: [pixi](https://pixi.sh/) (preferred), uv, or conda
- Linting/formatting: [ruff](https://docs.astral.sh/ruff/)
- Schema validation: [Pydantic](https://docs.pydantic.dev/) v2
- CLI: [Typer](https://typer.tiangolo.com/)
- Tests: [pytest](https://docs.pytest.org/)

User stories in [`USER_STORIES.md`](USER_STORIES.md) drive both implementation and tests. Each story has an ID and testable acceptance criteria — implementations should reference the relevant `US-NN` ID in code comments and commit messages.

## Related work

Cairn sits in a small but rapidly evolving ecosystem of tools and specifications for AI-assisted research provenance and reproducibility. Peer projects worth knowing:

- **[ASTRA](https://astra-spec.org)** — Agentic Schema for Transparent Research and Analysis (Lanusse & Parker, 2026, Lightcone Research). An open specification for the scientific record itself, sharing Cairn's substrate-as-specification commitment.
- **[ARA](https://github.com/Orchestra-Research/Agent-Native-Research-Artifact)** — Agent-Native Research Artifact (Liu et al., 2026). Structured layout for crystallized research outputs with provenance tags for human vs. AI contributions.
- **[RO-Crate](https://www.researchobject.org/ro-crate/)** and **[W3C PROV](https://www.w3.org/TR/prov-overview/)** — foundational standards for research artifact packaging and provenance vocabulary.

Cairn captures the *living* state of a project — the group's accumulated thinking, day-to-day. ASTRA and ARA capture *crystallized* records of specific results, structured for external review. They compose: a cairn produces ASTRA- or ARA-compliant artifacts when work is ready to share.

## License

MIT