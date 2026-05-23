# Multi-user / multi-cairn UX testing plan

A test methodology for validating cairn's behavior under realistic multi-user and multi-cairn loads, exercised by **isolated sub-agents** that emulate distinct human users and report feedback in a uniform format that can be aggregated and synthesized.

> **Status: PLAN — not yet executed.** This directory holds the design for the test run. Execution happens once the plan is reviewed and merged. Each scenario doc is then handed to a sub-agent (or several) per the recipe below.

## Why this exists

Recent work shipped two surfaces whose interaction matters but hasn't been exercised under realistic load:

1. **One MCP server, many cairns** (ADR-0010) — the registry-based dispatch where every MCP tool accepts a `cairn` parameter naming the target. Single-cairn convenience defaulting handles the simple case; multi-cairn disambiguation is the case that needs testing.
2. **HTTP transport + remote-mode `cairn.toml`** (US-P-11 / US-P-12 / US-P-13, merged in PR #25) — one server reachable by multiple clients simultaneously, attribution via `state/collaborators.yaml`, credentials via env / `~/.config/cairn/credentials.toml`.

Together they enable two topologies that are now realistically deployable:

- **One user, many cairns.** A researcher with multiple projects opens parallel Claude Code sessions in different project repos. Each session must route writes to the right cairn without confusion. Discoverable via `cairn.toml`'s `name` field plus the user's MCP registry.
- **Many users, one cairn.** A research group sharing a single cairn (typically hosted via HTTP transport on a group machine) writes concurrently from multiple sessions. Attribution must remain correct; concurrent writes to the same state file must serialize cleanly; identity-based behaviors (`whoami`, suggested-author matching) must work per-user.

This plan exercises both topologies with sub-agent emulation, captures structured feedback per sub-agent, and produces an aggregate report against acceptance criteria that map back to the corresponding user stories.

## Scenarios

Detailed in their own files in this directory:

- **`scenario-1-one-user-many-cairns.md`** — one human, multiple cairns, multiple parallel sub-agent sessions.
- **`scenario-2-many-users-one-cairn.md`** — multiple humans (sub-agent-emulated), one shared cairn.
- *(Scenario 3 — many users, many cairns — deliberately out of scope for this round. It's the composition of 1 and 2; if both pass cleanly, 3 is unlikely to surface new failure modes worth the test cost. Revisit if signal from 1 or 2 motivates it.)*

## Methodology — sub-agent emulation

The unit of test is a **sub-agent run**: a fresh Claude Code-style agent invoked via the Agent tool, given:

1. An **identity** (a collaborator id pre-registered in the relevant cairn, plus a one-line role).
2. A **target environment** — which cairn (or cairns), where, and the credentials / transport in use.
3. A **work backlog** — a small markdown file naming a few cairn-relevant tasks the sub-agent should perform (capture a decision, log a finding, complete an action, ask a clarifying question, etc.). The backlog is deliberately not exhaustive — it gives the agent enough context to do realistic work without scripting every move.
4. A **feedback template** — what the agent reports back at the end of its run.

Each sub-agent works in its own tmpdir, against its own copy of the registry config (`XDG_CONFIG_HOME` pointed at a per-agent isolation dir), and reports feedback as a markdown file that the orchestrator (this session, or me) aggregates.

The key constraint: **sub-agents do not see each other's transcripts**. They report only via the feedback template. This forces failure modes to be observable in the feedback artifacts, not in conversational context — which is how a real research group would experience them.

## Dummy projects (fictional, not real-repo)

For both scenarios we use **small fictional project fixtures** rather than cloning real public repositories. Tradeoffs:

- **Pros** of fictional: deterministic; no risk of accidental push to real repos; lightweight; tests are reproducible across runs.
- **Cons** of fictional: less realistic project history (synthesized commit log, synthesized README); a real repo's organic structure isn't reproduced.

For *bootstrap-quality* testing the fictional choice loses some realism — but this plan isn't testing bootstrap. It's testing concurrent / multi-cairn / multi-user behaviors where the project content is mostly atmosphere. The work backlogs supply the necessary substance.

Three fictional projects support the scenarios:

- **`coral-bleach`** — a marine-biology data analysis project. Used as Cairn A in scenario 1.
- **`lit-monitor`** — a literature-monitoring tool project. Used as Cairn B in scenario 1.
- **`shared-physics-paper`** — a multi-author paper-writing project. Used as the single shared cairn in scenario 2.

Each fixture is described in `fixtures/README.md`. They live as tmpdir-buildable specs (a list of files + content + a synthesized git history), not as committed checked-in directories — so the test isn't bloated and the fixtures can be regenerated cleanly on each run.

## Feedback collection and aggregation

Each sub-agent produces one feedback markdown file conforming to `feedback-template.md`. Files are placed under a run-specific output directory (e.g., `tests/agent_smoke/multi-user-multi-cairn/runs/<timestamp>/`).

After all sub-agent runs complete, the orchestrator (me) reads every feedback file and synthesizes:

- **Pass / partial / fail** against each scenario's acceptance criteria.
- **Technical findings** — bugs, schema gaps, error-message problems, concurrency issues. Each gets a one-line summary + a path back to the feedback file(s) that surfaced it.
- **UX findings** — friction, confusing prompts, mis-routings, agent-posture violations. Same treatment.
- **Recommendations** — concrete next moves, ranked. May reference existing issues / ADRs / open-questions where applicable.

The aggregate report is committed under `runs/<timestamp>/SYNTHESIS.md` so future readers (or future test runs) can compare.

## Execution recipe

When the plan is approved, the execution sequence is:

1. **Set up fixtures.** Build the three fictional project skeletons in tmpdir. Each gets a synthesized git history, a README, and any other minimum-viable artifacts the scenario calls for.

2. **Set up cairns.** Scaffold the cairns the scenarios need. For scenario 1, two cairns owned by one user; for scenario 2, one cairn with three pre-registered collaborators.

3. **For scenario 1**: launch ~2–3 parallel sub-agents (via the Agent tool with `run_in_background=true`), each pointed at a different cairn. Wait for completion. Collect feedback files.

4. **For scenario 2**: launch ~3 parallel sub-agents, each as a distinct collaborator working in the same cairn. Wait for completion. Collect feedback files.

5. **Synthesize.** Read all feedback, write `SYNTHESIS.md`, commit.

6. **Decide.** Based on synthesis: file issues for technical bugs, draft ADRs for design tensions, open follow-up PRs for low-cost fixes.

The scenarios are designed to be **idempotent and isolated** — each run uses fresh tmpdirs, fresh registry configs, and fresh sub-agent contexts. Re-running is safe and produces a clean comparison set.

## Acceptance criteria for "the plan worked"

This plan itself succeeds when, at the end of execution:

- Each scenario's acceptance criteria (in the scenario doc) are evaluated against feedback.
- The `SYNTHESIS.md` lists concrete findings and recommendations.
- At least one of the following holds:
  - Recommendations land as new GitHub issues / ADRs / open-question entries, *or*
  - The scenarios passed cleanly and the synthesis says so plainly (still a useful artifact).

If the methodology turns out to surface things that ad-hoc testing wouldn't, the pattern stays in `tests/agent_smoke/` for re-use; if it produces only noise, the pattern is documented as not-recommended and the directory's history serves as the record.

## What this plan is NOT

- Not a Python pytest integration test. The Claude Agent SDK isn't wired into pytest in this repo yet; the existing `bootstrap-smoke-test` skill is the same shape (a SKILL.md-style doc handed to a sub-agent) and remains the prototype until headless `claude -p` / SDK-driven CI lands. This plan inherits that posture.
- Not a load test. Sub-agent count is small (2–3 per scenario); we're testing for correctness under concurrency, not throughput.
- Not a security test. HTTP transport ships with `attribution, not authentication` per Issue #22; auth-binding is a deferred ADR. This plan doesn't pretend to exercise that surface.
- Not exhaustive. Scenario 3 (many users × many cairns) is skipped as composition; rare interactions specific to a real HTTP deployment (e.g., bearer-token rotation mid-session) aren't covered.

## Files in this directory

- `README.md` (this file) — methodology + scope.
- `scenario-1-one-user-many-cairns.md` — full description, user-story, sub-agent recipe, acceptance criteria.
- `scenario-2-many-users-one-cairn.md` — same.
- `feedback-template.md` — what each sub-agent reports back.
- `fixtures/README.md` — design of the three fictional projects.

Once executed, `runs/<timestamp>/` will hold the per-run feedback files and the synthesis report.
