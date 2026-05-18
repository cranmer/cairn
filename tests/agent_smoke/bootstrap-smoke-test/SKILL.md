---
name: bootstrap-smoke-test
description: Use to smoke-test AGENT-BOOTSTRAP.md end-to-end against the current working tree. A fresh agent (subagent or `claude -p`) follows the bootstrap doc against a fixture project repo in a tmpdir, runs structural checks on the resulting cairn, and reports back where the doc was clear vs ambiguous. Catches regressions in the bootstrap UX before they reach a real user. NOT a cairn-substrate skill — this is a development tool for the Cairn framework itself.
---

# Bootstrap smoke test

End-to-end test of `AGENT-BOOTSTRAP.md` driven by a fresh Claude Code agent. The system under test is the *combination* of the bootstrap doc, the `cairn` CLI, and the agent's ability to follow prose instructions — none of which a Python unit test covers.

This skill is a **development tool for the Cairn framework**. It does not ship into cairns and is not invoked by end users. Run it by launching a subagent (during a Claude Code session in this repo) with this file's contents as the prompt, or by an automated harness (see *Future: pytest + CI* below).

## What this skill does

1. Sets up a fixture: clones `karpathy/nanoGPT` (a small, real ML research project) into a tmpdir as the simulated "user's project repo".
2. Follows `AGENT-BOOTSTRAP.md` end-to-end as if a fresh Claude Code agent had been pasted the bootstrap doc by a user.
3. Treats itself as both the agent and the user — at each ★ confirmation mark, picks a preset autopilot default (below), notes the choice, and proceeds without stopping.
4. Uses agent capabilities the bootstrap doc envisions: reads the fixture's README, scans its file tree and recent git log, and uses that signal to populate `PROJECT.md`'s Overview / Current focus / Related repositories sections before the first commit.
5. Runs structural checks on the resulting cairn and reports back in a fixed format (below).

## One critical override

**Do NOT install Cairn from GitHub** as the bootstrap doc instructs. The doc tells the agent to run `pipx install git+https://github.com/cranmer/cairn`, which installs whatever is on `main`. The smoke test must exercise the *current working tree*. Install from the local checkout at `/home/user/cairn` instead — use whichever method works in the host environment (`pip install -e /home/user/cairn` is usually fine; pipx may not be available). Record the install method used in the report.

## Autopilot defaults for ★ marks

- **Step 2 (install Cairn)** — overridden as above. Document the install path taken.
- **Step 3 (git identity)** — use whatever the host already has set globally. Don't change it. If neither name nor email is set, stop and report (the test can't proceed without an identity, and inventing one violates Cairn's substrate-as-truth principle).
- **Step 4 (where the cairn lives)** — project name `nanogpt-cairn`. Parent directory: the tmpdir created in step 1 (so the cairn lands as a sibling of the cloned `nanoGPT/`). Pass `--no-input`.
- **Step 5 (first collaborator)** — id `kyle`, name `Kyle Cranmer`, role `developing generative models for physics` (activity-based, per the doc's anti-titles guidance). GitHub handle `cranmer`. One expertise tag: `machine learning`.
- **Step 6.5 (env-based-install PATH fix)** — only do this if the install path from step 2 actually requires it (it won't, for `pip install -e`).

## Structural checks

After the bootstrap finishes, verify and report each item as PASS / FAIL / MISSING-AS-EXPECTED:

- `<cairn>/PROJECT.md` exists with Overview / Current focus / Related repositories populated from real nanoGPT signal (no TODO placeholders).
- `<cairn>/state/collaborators.yaml` has the `kyle` entry.
- `git log --oneline` in the cairn shows the scaffold commit + the collaborator-add commit (+ a PROJECT.md edit commit if one was made).
- `cairn validate` exits 0.
- `cairn status` produces sensible output.
- A `.cairn` marker file at the cairn root. **Currently expected to be MISSING** — the marker is planned (ADR-0006) but not yet shipped. Reporting confirms current state.
- All seven bundled skills (`orient`, `search-history`, `start-branch`, `resolve-branch`, `complete-action`, `log-finding`, `debrief`) landed under `<cairn>/skills/`.

## Report format

Structure the deliverable as:

1. **Outcome** — did the bootstrap succeed end-to-end? One paragraph.
2. **Where the doc was clear vs ambiguous** — concrete examples with quoted lines from `AGENT-BOOTSTRAP.md`. This is the highest-value section; be specific.
3. **Where the agent had to deviate from the doc** (besides the install override) — and why.
4. **PROJECT.md content** — paste the Overview / Current focus / Related repositories sections written. Lets a reviewer judge agent-driven population quality.
5. **Structural check results** — table with one row per item above.
6. **Recommendations** — top 3–5 concrete doc fixes.

Be honest about friction. The point is to find problems, not to make the doc look good.

## Constraints

- Don't push anything to any git remote. Local commits only.
- Don't modify `/home/user/cairn` itself — that's the framework repo under test. All work goes in the tmpdir.
- A few minutes reading nanoGPT's README and a quick file-tree scan is enough signal for `PROJECT.md` population — don't go deeper.
- If a blocker needs human input, stop and report rather than thrashing.

## Future: pytest + CI

This recipe is the prototype shape; the durable version is a gated pytest integration test (probably `tests/integration/test_bootstrap_e2e.py`) that drives the same loop via the Claude Agent SDK or headless `claude -p`. Plan:

- **Marker**: `@pytest.mark.integration`, opt-in (`pytest -m integration`), so it doesn't run on every local `pytest`.
- **Assertion style**: structural invariants only (file exists, schema validates, sections present). Never byte-equality — the agent's output isn't deterministic.
- **Model pin and `max_turns` cap**: pin a specific model ID; cap turns so a flake can't burn unbounded budget.
- **CI trigger**: GitHub Actions with `ANTHROPIC_API_KEY` as a repo secret. Fire on PRs that touch `AGENT-BOOTSTRAP.md`, `QUICKSTART.md`, or `templates/default/skills/`, plus a weekly cron. **Not on every PR** — each run is real money.
- **Fork safety**: PRs from forks won't have the secret. Use `pull_request_target` or restrict the workflow to branches in the main repo.
- **Source of truth**: the pytest test's prompt should be this SKILL.md's contents (loaded via `Path(...).read_text()`), not a duplicated string. One file, two consumers (subagent and pytest).
