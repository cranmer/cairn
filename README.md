# Cairn

> A tool and design standard for hybrid human/AI research collaboration.

Cairn defines a repository structure, file schemas, and conventions for maintaining a research group's shared project memory — designed for a world where AI agents contribute alongside humans. The substrate is a git repository; everything else (agents, indices, dashboards, MCP servers) is a layer on top that can be added or replaced without compromising the source of truth.

**Two terms to know:**

- **Cairn** (capitalized) is the framework — this repo, the Python package, the conventions.
- **a cairn** (lowercase) is an instance — one research project's repository organized following Cairn's conventions. A research group runs one cairn per project.

**A cairn is not a project's code repo.** A typical research project already has one or more git repos for its code, analyses, paper, and data; the cairn is a *separate*, additional repo that lives alongside them and holds the group's shared memory — decisions, open questions, findings, action items, meeting notes — that doesn't naturally fit inside any one code repo. The cairn references the others (via free-form notes for now, structured cross-references later) without containing them.

**Augmentation, not replacement.** Cairn does not ask collaborators to change how they work. You keep using your normal tools — git, Zoom, Slack, email, conversation — at your normal rhythm. An agent listens in those native channels and writes structured notes into the cairn as a side effect, so other collaborators (and future agents, and you three months later) can catch up on the structured view without having been in the room. The principle is captured in [`docs/decisions/0007-augmentation-not-replacement.md`](docs/decisions/0007-augmentation-not-replacement.md) and pairs with the existing substrate-as-specification commitment: the former says *where work happens* (in your native channels); the latter says *where state lives* (files in git).

**MCP-first.** The primary integration is an MCP server (`cairn mcp`) that exposes ~28 read and write tools to any Claude Code session. One server serves all of a user's cairns (per [ADR-0010](docs/decisions/0010-single-mcp-server-multiple-cairns.md)); each MCP tool accepts a `cairn` parameter naming the target, defaulting to the only registered one when there's just one. Wire it up once with `claude mcp add cairn cairn mcp` and every session anywhere has access to the cairn without `cd` or per-session bootstrap.

**Two access modes — client and server.** Most of the time you're in **client mode**: a Claude Code session opened in your project's code repo (or, in future, a Zoom transcript / Slack thread), with the cairn as a transparent backend the agent calls into via MCP. This is the everyday case and the primary surface. **Server mode** — a session opened inside the cairn directory — is for occasional maintenance: deep debriefs, restructuring, planning meetings, spelunking through accumulated history. See [`docs/decisions/0008-client-server-and-exploration-rename.md`](docs/decisions/0008-client-server-and-exploration-rename.md).

> **Status:** Phase 0–2 mostly shipped, Phase 3 (MCP server) shipped and being UX-tested. The Python package scaffolds new cairns, manages collaborators / decisions / findings / actions / open questions, validates state, exposes MCP tools, and supports retroactive bootstrap from existing project repos. See [QUICKSTART.md](QUICKSTART.md) for a five-minute tour. For the full vision, see [the design overview](docs/overview.html).

## What it enables

- **Persistent shared memory** across meetings, decisions, findings, and discussions.
- **Async contribution and recall** — collaborators (and their agents) can ask what was decided, what was discussed, and what's outstanding without sitting through the original conversation.
- **Parallel exploration** — your project repo's git branches stay yours; the cairn optionally tracks the *rationale* of alternative inquiries (decisions, methodology choices, branching investigations) via tracked explorations when the comparison itself is the artifact worth preserving.
- **Uniform interface for human and AI collaborators** — same workflows, attributed identities.
- **Reproducible artifact export** into emerging community standards (ASTRA, ARA, RO-Crate).

## Documentation

| Document | Purpose |
|----------|---------|
| [QUICKSTART.md](QUICKSTART.md) | Canonical install + first-cairn setup, written for a human reader. Two scenarios: start-from-scratch vs bootstrap-from-existing-repo |
| [AGENT-BOOTSTRAP.md](AGENT-BOOTSTRAP.md) | Same setup, written for an agent (paste into Claude Code). Second-person tone, ★ confirmation marks, ends with a bootstrap-from-repo handoff for Scenario B |
| [docs/overview.html](docs/overview.html) | Polished overview for sharing with colleagues |
| [docs/splash.html](docs/splash.html) | Single-page introduction |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Design document — principles, components, build path |
| [USER_STORIES.md](USER_STORIES.md) | Specifications for the Python package, agent skills, and MCP server |
| [CLAUDE.md](CLAUDE.md) | Development guide for Claude Code sessions |
| [docs/decisions/](docs/decisions/) | Architectural decision records (ADRs) |
| [docs/open-questions.md](docs/open-questions.md) | Unresolved design tensions awaiting ADRs |

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
├── .github/workflows/             # CI: editable-install tests + wheel-install smoke
├── src/cairn/                     # Python package source
│   ├── schemas/                   # Pydantic v2 models for the five state files
│   ├── io/                        # YAML load/dump + state-file I/O
│   ├── template/                  # Jinja2 renderer for `cairn init` templates
│   ├── templates/                 # bundled cairn template (ships inside the wheel)
│   │   └── default/{{cookiecutter.project_name}}/
│   │       ├── skills/            # bundled SKILL.md files (orient, search-history, …)
│   │       └── .claude/           # SessionStart hook so opened sessions auto-orient
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

- [x] **Phase 0 — Foundation** *(done)*: canonical template, Pydantic v2 schemas, `cairn init`, basic state-write CLIs.
- [x] **Phase 1 — Agent skills** *(done)*: bundled SKILL.md files (`orient`, `log-finding`, `log-decision`, `log-action`, `start-exploration`, `resolve-exploration`, `complete-action`, `search-history`, `debrief`, `bootstrap_from_repo`).
- [x] **Phase 3 — MCP server** *(shipped, UX-testing)*: `cairn mcp` stdio server, single-server-many-cairns registry (ADR-0010), ~28 read/write tools, `cairn.toml` project-repo pairing, semantic PROJECT.md tools, backdating + structured PR / commit provenance, skill discoverability.
- [ ] **Phase 2 — Python package extensions** *(in progress)*: artifact export (ASTRA / ARA / RO-Crate, US-P-08), meeting import (US-P-07), agenda draft (US-P-09).
- [ ] **ADR-0011** *(drafted)*: multi-author attribution. Plural authorship on the four writable entity types. Awaiting review before implementation.
- [ ] **Phase 4** — Meeting capture (Whisper + pyannote diarization).
- [ ] **Phase 5** — AI collaborator runtime (literature monitor, etc.).
- [ ] **Phase 6** — Voice-mode meeting participant *(long-term)*.

## Available commands

Once installed (`pipx install 'cairn[mcp] @ git+https://github.com/cranmer/cairn'`):

**MCP / registry:**
| Command | Purpose |
|---------|---------|
| `cairn mcp` | Run the MCP server over stdio (configured via `claude mcp add cairn cairn mcp`) |
| `cairn register <name> <path>` | Add a cairn to the user-level MCP registry. `--init` scaffolds it if missing |
| `cairn unregister <name>` | Remove a cairn from the registry |
| `cairn registered` | List currently registered cairns |
| `cairn link [<project-repo>]` | Write a `cairn.toml` at a project repo root pairing it with a cairn by name |
| `cairn skills sync` | Backfill bundled skills into an existing cairn (after a cairn package upgrade) |

**Cairn-state commands (also available as MCP tools):**
| Command | Purpose |
|---------|---------|
| `cairn init <name>` | Scaffold a new cairn from the bundled template |
| `cairn collaborator add` | Register a human, AI, group, or unknown-type collaborator |
| `cairn decision add` | Record a decision with auto ID and structured PR / commit provenance |
| `cairn action add` / `complete` | Add or complete action items |
| `cairn exploration start` / `close` | Open or close a tracked exploration (alternative line of inquiry) |
| `cairn finding add` | Write a finding with YAML frontmatter, optionally backdated |
| `cairn validate` | Check schemas, cross-references, and meeting filenames |
| `cairn status` | Compact project-state summary; supports `--json` and `--branch` |
| `cairn orient` | Print PROJECT.md plus the status block in one go |
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