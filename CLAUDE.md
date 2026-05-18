# Cairn — Development Guide

This repository is the development home of **Cairn**, a tool and design standard for hybrid human/AI research collaboration. Read this file first; deeper context lives in the documents referenced below.

## What Cairn is

Cairn defines a repository structure, file schemas, and conventions for maintaining a research group's shared project memory. The substrate is a git repository organized following Cairn's conventions — *a cairn*. Around this substrate, Cairn provides a Python package for scaffolding and managing cairns, plus reference patterns for layered augmentations (MCP server, meeting capture, AI collaborators).

**Capitalization matters.** "Cairn" (capitalized) is the framework — this repo, the package, the conventions. "a cairn" (lowercase) is an instance — a specific research project's repository following those conventions. Maintain this distinction in code, docs, commits, and conversation.

## Where to find what

- `ARCHITECTURE.md` — the design document. Read before making structural changes.
- `USER_STORIES.md` — testable user stories. The primary specification. When implementing a feature, reference the relevant `US-NN` ID.
- `figures/` — architecture diagrams referenced by ARCHITECTURE.md.
- `docs/overview.html` — polished overview for sharing with colleagues.
- `docs/splash.html` — splash page.
- `templates/default/` — the canonical cairn template that `cairn init` will scaffold from (to be built).
- `src/cairn/` — the Python package source (to be built).

## Current phase

**Phase 0 (Foundation) is complete.** Shipped: the canonical template at `templates/default/`, Pydantic v2 schemas for the five state files, and the CLI commands `cairn init`, `cairn collaborator add`, `cairn decision add`, `cairn validate`, `cairn status` (US-P-01 through US-P-06). 64 tests passing. See `docs/decisions/` for ADRs locking in YAML library, git library, template engine, and ID/timestamp conventions.

**Phase 1 (Agent skills + supporting commands) is complete.** Shipped: `cairn branch start`, `cairn branch close`, `cairn action add`, `cairn action complete`, and bundled Claude Code-style `SKILL.md` files in `templates/default/skills/` (`orient`, `search-history`, `start-branch`, `resolve-branch`, `complete-action`, `log-finding`) that ship into newly-scaffolded cairns via `cairn init`. Covers US-A-01, US-A-03, US-A-04, US-A-05, US-A-09 (plus US-A-02 from Phase 2). Branch lifecycle now has both halves — opening and closing — so exploration branches don't accumulate without resolution.

**Phase 2 — Python package extensions — is in progress.** Targets and status:

- [x] US-A-02 + `cairn finding add`: finding files at `knowledge/findings/YYYY-MM-DD-<slug>.md` with YAML frontmatter (date, author, title, slug, related, branch). Bundled `log-finding` skill in `templates/default/skills/`. `cairn validate` checks finding filenames, frontmatter schema, author/related cross-references.
- [ ] US-P-07: Meeting import — `cairn meeting import --from zoom <file>` produces `knowledge/meetings/YYYY-MM-DD.md` with frontmatter and an optional `<date>-staged.yaml` of inferred decisions / action items for human review.
- [ ] US-P-08: Artifact export — `cairn artifact export --format <astra|ara|ro-crate>` produces a directory in the chosen specification's layout. Stubs that pass schema validation are acceptable early.
- [ ] US-P-09: Agenda draft — `cairn agenda draft --since <date|last-meeting>` writes a markdown agenda assembled from flagged items, branches needing review, recent open questions, due action items, and recent findings.

Out of scope until later phases: MCP server (Phase 3), meeting capture automation (Phase 4), AI collaborator runtime with scheduling/permissions enforcement (Phase 5), voice mode (Phase 6), artifact export (Phase 2 / US-P-08), meeting import (Phase 2 / US-P-07). Don't speculatively scaffold these.

## Backlog (not yet phased)

Carried items that are not blocking a phase but should be picked up when convenient:

- ~~Agent-driven bootstrap doc~~ — *done*. `AGENT-BOOTSTRAP.md` lives at the repo root and is linked from `QUICKSTART.md`.

## Development conventions

- **Python 3.10+**.
- **Environment management**: pixi (preferred — the project lead uses it; tooling that works under pixi will work under uv/conda too).
- **Schema validation**: Pydantic v2 for state file schemas. Schemas in `src/cairn/schemas/`.
- **CLI**: Typer.
- **Tests**: pytest. The user stories in USER_STORIES.md are the primary specification — each story should yield one or more test functions, named to reference its `US-NN` ID where possible.
- **Style**: ruff for both linting and formatting.
- **Package layout**: `src/cairn/` layout (not flat).

## Working in this repo

When asked to implement a user story, reference the relevant `US-NN` ID and let the acceptance criteria drive both implementation and tests. Build the smallest version that satisfies the criteria; resist speculative features.

When making non-trivial design decisions during implementation (schema field choices, library selections, file naming conventions), record them as short Architectural Decision Records (ADRs) under `docs/decisions/`. Format: title, context, decision, consequences. One file per decision.

When in doubt about Cairn's principles, the **substrate-as-specification commitment** takes precedence: implementations should not require a particular service or platform. Anything the Python package does should be expressible in terms of files in the repo.

## Invariants to preserve

These should hold across everything built in this repo:

- **Attribution end-to-end.** Every write through any interface records the actor's identity. Git authorship for humans; a configured agent identity (in `state/collaborators.yaml`) for AI collaborators.
- **Source of truth is the repo.** Anything else (vector indices, MCP server caches, computed summaries) is derived and must be reproducible from the repo. Stop-and-rebuild produces identical results.
- **Validation visibility.** Schema violations and broken cross-references produce clear errors with enough context to fix. Never silent corruption.
- **Branch semantics consistency.** Operations scoped to a branch see that branch's view, not main's.

## Related work to be aware of

- **ASTRA** (Lanusse & Parker, 2026 — astra-spec.org) is an open specification for the scientific record itself. Shares Cairn's substrate-as-specification commitment but at a different scope (a vetted analysis, vs Cairn's living project state).
- **ARA** (Liu et al., 2026 — Agent-Native Research Artifact) is a structured layout for crystallized research outputs.

These are peer projects in adjacent problem spaces, not dependencies. Cairn defers to them for the artifact format inside `knowledge/provenance/` of a cairn. Don't reimplement what they're already specifying; instead, plan for `cairn artifact export` to produce ASTRA-compliant or ARA-compliant outputs (US-P-08).

## Commit and PR conventions

- Commit messages should reference user story IDs where applicable (`US-P-01: scaffold cairn init`).
- PRs against `main` go through review; the canonical state of the framework is what's on main.
- Use feature branches named `<your-id>/<short-description>` (mirroring the convention cairns themselves use).

## When uncertain

Two good fallbacks:
- Re-read ARCHITECTURE.md §Architectural Principles. The five principles resolve most ambiguity.
- Ask before assuming. A short clarifying question costs less than a wrong direction taken confidently.
