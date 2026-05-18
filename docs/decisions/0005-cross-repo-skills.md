# 0005 — Cross-repo skills distribution (Mode A for v0; Mode B as B1, deferred)

> **Note (superseded in part):** the four-step resolution sketch in the B1 section below has been replaced by ADR-0006, which redesigns discovery around a `.cairn` root marker, a `cairn.toml` project-repo pointer file, and a `CairnTarget` abstraction for future MCP backends. The B1-vs-B2-vs-B3 decision and the Mode A v0 commitment in this ADR still stand.

## Context

A cairn is intentionally a separate git repo from a project's working code/data/paper repos (see README.md, ARCHITECTURE.md §Repository Structure, US-P-10). That means an agent working with a user can be in one of two places when "cairn-relevant" things happen:

- **Mode A — the user's Claude Code session is open inside the cairn directory.** The SessionStart hook in `<cairn>/.claude/settings.json` fires; the agent reads `<cairn>/skills/<name>/SKILL.md`; `cairn status` runs automatically. Natural for *curating* the cairn: planning a meeting, debriefing, reviewing decisions, drafting an agenda. This is what we shipped in Phase 1 and what AGENT-BOOTSTRAP.md walks through.

- **Mode B — the user's Claude Code session is open inside a project's working repo**, and the cairn lives elsewhere on disk (e.g., `~/projects/foo/` for the code, `~/projects/foo-cairn/` for the cairn). This is the *common* case once a project is running — most of the user's time is in code, and the cairn is the coordination layer they touch periodically. Today the agent in Mode B has no visibility into the associated cairn at all: no SessionStart hook, no `skills/<name>/SKILL.md`, no awareness that one exists.

The tracking-stance posture introduced in TRACKING.md (capture eagerly during conversation; agent does the work the user shouldn't have to) only pays off in Mode B — that's where the substantive *project* conversation happens. Mode A captures are mostly meta-work about the cairn itself. So Mode B coverage is the win we want eventually. But getting there involves a design decision about how cairn's skills are packaged and discovered.

Three options surfaced during a user-experience review:

### B1 — global skills install + cairn discovery

`pipx install cairn` (or a one-time `cairn install-skills` command) copies the bundled SKILL.md files from `cairn/templates/default/.../skills/` into the user's `~/.claude/skills/cairn-<name>/` (or `~/.claude/skills/cairn/<name>/`). Once installed, every Claude Code session everywhere has the cairn skills available — they show up in `/skills`, and the user can type `/orient`, `/log-finding`, `/debrief`, etc.

When invoked, a skill needs to know *which cairn* to write to. Resolution options, in order:

1. Walk up from cwd looking for a cairn marker (`state/collaborators.yaml`). Resolves the user-is-in-the-cairn case naturally.
2. If not found, check an environment variable (`CAIRN_PATH`).
3. If not set, check a user-level config (`~/.config/cairn/config.toml` or `~/.cairnrc`) for either a single `default_cairn:` path or a directory-prefix map: `~/projects/foo/* -> ~/projects/foo-cairn/`.
4. If still ambiguous, ask the user once and offer to record the choice in the user-level config for next time.

**Pros**: matches how Claude Code skills are designed to be distributed; gives Mode B full coverage; the skill set becomes part of the user's ambient agent toolkit, not per-project plumbing.

**Cons**: introduces user-level state for cairn (the config + the installed skills dir); discovery logic is genuinely new code; the same `pipx install` now has a side effect outside the venv (writes to `~/.claude/skills/`), which some users will find surprising. Mitigation: gate the side-effect behind an explicit `cairn install-skills` command, not on every `pipx install`.

### B2 — per-project pointer file *(rejected)*

The bootstrap writes a small `.claude/settings.json` *into the user's project repo* with the cairn's path and a SessionStart hook that loads skills from `<cairn>/skills/`. Concretely: when `cairn init --for-project ~/projects/foo` runs, it writes `~/projects/foo/.claude/settings.json` alongside creating the cairn.

**Rejected because** it violates US-P-10's "purely additive — cairn does not modify any of the existing project repos" promise. Each project repo would carry cairn-specific configuration, which spreads coupling outside the cairn and makes the project repo's `.claude/` directory non-portable. Also creates ambiguity if the user later opts out: now there's a stale pointer file in their project repo.

### B3 — two sessions, document Mode A

Keep things as they are. Document plainly: *for cairn work, open Claude Code inside the cairn directory. Code work happens in a separate session inside the project repo.* The tracking stance works as designed inside cairn sessions; the user manually surfaces things from a code session into the cairn session (or runs the debrief skill at the end of a cairn session to bulk-capture).

**Pros**: ships today; zero new infrastructure; conceptually clear; no global state.

**Cons**: friction — the user has to remember which session is which; the tracking stance applies only inside the cairn session, which is the wrong place for most capture-worthy conversation; users will end up either (i) forgetting to capture things from code sessions or (ii) running two sessions side-by-side and copy/pasting between them.

## Decision

For v0:

1. **Ship Mode A as the supported access pattern.** Make this the explicit convention in README, ARCHITECTURE, and AGENT-BOOTSTRAP. Tell users (and agents reading AGENT-BOOTSTRAP) plainly: cairn work happens inside the cairn directory in its own Claude Code session.
2. **Adopt B1 as the planned answer for Mode B**, deferred to a future phase (Phase 2 or 3 depending on bandwidth). Capture the design in this ADR so the direction is on record. Do not implement yet — implement once we have enough usage data from Mode A to know if the discovery convention in B1 holds up.
3. **Do not ship B2** (per-project pointer files), now or later. Modifying project repos to enable cairn is the wrong shape.

## Consequences

- AGENT-BOOTSTRAP.md, README.md, ARCHITECTURE.md need a short, explicit statement of Mode A as the v0 convention. Without this, agents and users will reinvent ad-hoc Mode B workarounds (manually `cd`ing between repos, copy-pasting, asking the agent to "remember to log this later"). Done in the same commit as this ADR.
- US-P-10's bootstrap-from-existing-project flow has to live with the constraint that, after `cairn init` creates the cairn alongside the project repo, the user's Claude Code session for cairn work is in the cairn — not in the project repo where the agent did the pre-population. The AGENT-BOOTSTRAP doc should `cd` the user (and the agent) into the cairn explicitly at the end of Step 4, and frame the subsequent sessions as "open Claude Code here for cairn work."
- When we eventually build B1, the skill files we already ship at `cairn/templates/default/.../skills/` become the source of truth for the install — the templates and the global install are the same files, copied. No duplication.
- The cairn-discovery convention in B1 (cwd-walk + env var + user config) is forward-compatible with Mode A: an agent inside the cairn finds the cairn via the cwd walk, which is the same answer the SessionStart hook gives today.
- **Trigger for revisiting**: real users (more than one) reporting that the two-session split is the dominant source of friction. Until then, the trade-off (less infra, more session-switching) is the better posture.
