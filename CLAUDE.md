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

**Phase 1 — Agent skills + supporting commands — is the current focus.** Goal: make a cairn useful inside a Claude Code session by bundling Claude Code-style `SKILL.md` files that read and write through the structure Phase 0 built. Targets:

- Bundled `SKILL.md` files in `templates/default/skills/` so newly-scaffolded cairns ship with them.
- US-A-01: Orient at session start — agent reads `PROJECT.md` + `state/collaborators.yaml`, identifies the user, produces a coherent summary citing recent decisions and open questions.
- US-A-03: Create an exploration branch — `cairn branch start <description>` creates `<user-id>/<kebab>` branch, updates `branches/README.md`, writes a branch manifest.
- US-A-04: Mark an action item complete — needs `cairn action add` and `cairn action complete <id>` (the `ActionItem` schema already exists from Phase 0).
- US-A-05: Search prior discussions — pure local file scan; can ship as a skill alone.

US-A-02 (log a finding mid-session) is deferred to Phase 2, alongside the other knowledge-base-writing primitives.

Out of scope until later phases: MCP server (Phase 3), meeting capture automation (Phase 4), AI collaborator runtime with scheduling/permissions enforcement (Phase 5), voice mode (Phase 6), artifact export (Phase 2 / US-P-08), meeting import (Phase 2 / US-P-07). Don't speculatively scaffold these.

## Development conventions

- **Python 3.11+**.
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
