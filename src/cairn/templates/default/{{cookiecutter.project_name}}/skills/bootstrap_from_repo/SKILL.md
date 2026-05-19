---
name: bootstrap_from_repo
description: Use when the user wants to seed a fresh cairn from an existing code repository's accumulated history — README, docs, git log, PR descriptions, CHANGELOG. Walks the repo, drafts a single batched proposal of inferred collaborators / decisions / findings / open questions / actions, gets one consent round, then writes each item to the cairn with correctly backdated dates and structured PR / commit provenance.
---

# Bootstrap a cairn from a project repository

When a user adopts cairn for an existing project, the cairn starts empty but the project usually doesn't — there are months or years of git history, README docs, PR descriptions, and CHANGELOG entries that already encode the project's decisions and findings. This skill seeds the new cairn from that material.

Posture: same as the `debrief` skill — survey eagerly, batch into a single consent proposal, then commit. Capture as the *recorded* form of what's already true, not as fresh judgement.

## When to trigger

- The user says any of: *"bootstrap the cairn from <repo>"*, *"seed this cairn from our existing project"*, *"fill in collaborators / decisions / findings from the project repo"*.
- The `status` tool's `suggested_next` field surfaces a non-null bootstrap hint (because the cairn is empty).
- A fresh cairn was just initialized alongside an existing project repo and the user starts asking about it.

Confirm with the user once before starting: *"I'll survey `<source-repo>` and propose a batched set of cairn entries inferred from its README, recent docs, and PR history. You'll get one consent pass before anything is written. Sound right?"*

## Steps

1. **Identify the source repo.** From the cairn's PROJECT.md "Related repositories" section, the project repo's `cairn.toml` upstream metadata, or by asking the user. Record its current HEAD SHA — that's the anchor for the bootstrap audit trail.

2. **Survey, don't write yet.** Read in this order:
   - `README.md` and any top-level docs.
   - `docs/decisions/` (if it exists — ADR-style content maps to cairn decisions almost 1:1).
   - `CHANGELOG.md` or release notes.
   - `git log --merges --first-parent main` for PR-merge commits in chronological order. Capture each PR's number, merge date, title, and short body.
   - `git shortlog -sn` for the contributor list.
   - Prominent `TODO` / `FIXME` markers, or whatever passes for "open questions" in the project (issues, design notes).

3. **Classify each artifact into a cairn type.** Use the four-way distinction:
   - **Decision** — a commitment with rationale. Most architectural choices in commit/PR titles. ADR files in `docs/decisions/` are *always* decisions.
   - **Finding** — an observed fact, measurement, or learned constraint. CHANGELOG entries describing "we discovered X" or "turns out Y" are findings. So are post-merge analyses.
   - **Open question** — uncertainty awaiting resolution. Open issues with no clear answer, `TODO` markers about "do we need X?" questions, design notes describing tradeoffs.
   - **Action item** — assigned, dated, pending work. Rare from historical repos (most actions are already complete by definition); prefer findings for "we did X" and skip dated actions for completed work.

4. **Draft a SINGLE batched proposal.** Group by type. For each item, show the user:
   - Type (decision / finding / question / action).
   - One-line summary.
   - Source — the PR / commit / file it came from.
   - Proposed `date` (the artifact's actual date, not today).
   - Proposed `source_prs` and/or `source_commits` (structured fields).
   - For decisions / findings: the rationale text that would populate `context` / `body`.

   Show collaborators in a separate sub-list. Limit each item summary to one line; the user is reviewing for inclusion, not editing prose at this stage.

5. **One consent round.** Ask: *"Drop any items I should skip, edit any that need fixing, or say 'go' to accept all."* Re-show the corrected list if the user changes anything, then proceed.

6. **Write, with backdated dates and structured provenance.** For each accepted item:
   - Collaborators first (so subsequent writes can reference them as authors): `add_collaborator(id, name, role, email, github)`. Match commit-author identities; prefer the user as `author` when authorship of the historical decision is genuinely a group call.
   - PROJECT.md sections: `set_project_overview`, `set_current_focus`, `set_related_repositories` — use these instead of editing PROJECT.md as a blob. The Overview can be 1–2 paragraphs drawn from the project README; Related repositories should list the project repo plus any sibling data/paper repos.
   - Decisions: `add_decision(author, text, context, date=<actual date>, source_prs=[...], source_commits=[...])`.
   - Findings: `add_finding(author, title, body, date=<actual date>, source_prs=[...], source_commits=[...])`.
   - Open questions: `add_open_question(raised_by, question, related=[...])`.
   - Actions: only if the user explicitly wants pending work tracked — most historical work is already done.

7. **Summarize and stop.** Report:
   - N collaborators registered, M decisions, K findings, etc.
   - Source repo + HEAD SHA you anchored against, so future readers can audit.
   - That the cairn now reflects the project's pre-cairn history as best the agent could reconstruct it.

## Ambiguous authorship — *don't default to the project lead*

Many bootstrap-derived findings are observations the agent made from the repo's docs, TODO markers, or general repo state — they aren't authored claims by any single person. For these, **do not silently attribute to the project lead** as a "speaks for the project" default. That hides the bootstrap origin and over-credits one collaborator.

The right pattern, until proper multi-author or meeting-linkage schema lands (see `docs/open-questions.md`):

1. **Register an "unknown" placeholder collaborator first**, once per cairn:

   ```
   add_collaborator(
     id="repo-history",
     name="Repository history",
     role="bootstrap-attribution placeholder for observations extracted from project docs / commit history",
     type="unknown",
   )
   ```

2. **Attribute ambiguous bootstrap observations to it** rather than to a human:

   ```
   add_finding(
     author="repo-history",
     title="VMEC-JAX is constrained to a fixed-resolution submodule",
     date="2026-04-16",
     source_commits=["..."],
     ...
   )
   ```

3. **Attribute observations that DO have a clear authoring human** (e.g., the PR's actual author for an ADR-style decision) to that human. Only use `repo-history` when no single human is plausibly the author.

If the project's working repo has a primary docs maintainer, you can also register them as a human collaborator (with their git email / github handle) and attribute docs-derived findings to them — but only when their authorship of the underlying docs is clear. If you're not sure, `repo-history` is the safer default.

## What not to do

- **Don't infer decisions the project artifacts don't actually support.** If a PR's title is ambiguous, leave it out or ask. Bootstrap should be conservative; live capture fills in the rest.
- **Don't fabricate `context` / rationale text.** If the source PR has no body, copy the PR title and add `(extracted from PR title; no rationale recorded in the original)` rather than inventing.
- **Don't backfill action items as completed work.** Use findings for things that were done. Actions are for pending, assigned work.
- **Don't write one item at a time without consent.** The whole point of the batch is to avoid 30 per-item interruptions. One consent gate, then go.
- **Don't dedupe against existing cairn state silently.** If the cairn already has a `kyle` collaborator and the git log shows commits by `Kyle Cranmer <kyle.cranmer@wisc.edu>`, surface that to the user — *"matched git author Kyle Cranmer to existing collaborator `kyle`; OK?"* — rather than guessing.

## Acceptance criteria

- Every written entity has its actual historical `date` (not the time the bootstrap ran).
- Decisions and findings extracted from PRs have `source_prs` and `source_commits` populated.
- The bootstrap is a single consent gate, not N per-item confirmations.
- PROJECT.md's Overview / Current focus / Related repositories sections are filled (not template placeholders).
- The user is told, at the end, which source repo + commit was the anchor.

## Future improvements (not yet shipped)

- **Bulk / transactional add** so the bootstrap is one commit in the cairn rather than N. Today the user sees N small commits; the timeline is still correct (because of backdated dates), but the cairn's git log is noisier than necessary.
- **`mark_bootstrapped(source_repo, source_commit)`** structured record. Today the audit trail is "I'll tell the user verbally what I anchored against"; eventually `status` should surface it.
