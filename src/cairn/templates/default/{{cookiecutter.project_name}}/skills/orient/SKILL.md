---
name: orient
description: Use when starting a session inside this cairn (or when the user asks "what's going on with this project?") to load enough context to be useful, without dumping the entire knowledge base into the prompt. Loads PROJECT.md, the collaborator list, and a project-status summary, then identifies the current user.
---

# Orient at session start

You are starting a session in a *cairn* — a git-native research project repository. This skill loads the right context efficiently.

> **Note**: this cairn ships a Claude Code SessionStart hook in `.claude/settings.json` that already runs `cairn status` for you. If you can see fresh `cairn status` output in your initial context, you can skip step 3 below and go straight to interpreting it.

## Steps

1. **Read `PROJECT.md`** first. It is short by design and points at where things live.

1a. **Read `TRACKING.md`.** This is the project's posture guide for *how* you should capture state from the working conversation — cairn is built so the user doesn't have to invoke CLI commands by hand. Internalize the signals-to-listen-for table before the conversation starts.

2. **Read `state/collaborators.yaml`**. This identifies who's on the project. Match the current user by:
   - the configured git identity (`git config user.email`), against each collaborator's `github` or email field if present;
   - if no match, ask the user which collaborator id is theirs and note it for the session.

3. **Run `cairn status`** to get a compact summary of: open question count, incomplete action items (overdue / this week / upcoming), recent decisions, latest meeting. This is bounded in size by design (≤30 lines).

4. **Do *not* eagerly load:**
   - meeting transcripts in `knowledge/meetings/`
   - all findings in `knowledge/findings/`
   - the literature folder
   Load these on demand when the user's question requires them.

## Producing the orientation summary

When the user asks "what's going on with this project?" or similar, produce:

- A one- or two-sentence project description from `PROJECT.md`'s overview.
- The 3–5 most recent decisions, citing their IDs (`D-NNN`) from `cairn status`.
- Open questions worth flagging (up to 3), citing their IDs (`Q-NNN`).
- Any overdue action items, with assignee and ID.
- The date of the latest meeting.

Keep it under 200 words unless asked for more. Cite specific IDs so the user can follow up.

## Acceptance criteria (US-A-01)

- Time to first response is fast — no scan of the entire knowledge base.
- The user feels recognized: their identity in `state/collaborators.yaml` is acknowledged.
- Answers are grounded in canonical state, not invented.
