# How to track for this project

*Agent-facing posture guide. Edit this file if your group wants a different style of tracking; the schemas and CLI don't depend on it — it's purely guidance for the agent working in this cairn.*

## Default posture: capture eagerly, surface briefly

You (the agent) are responsible for keeping this project's running record. The user should not have to issue explicit `cairn finding add` / `cairn decision add` / `cairn action add` commands — that's git-flavored discipline, and the point of this cairn is that the agent does that work transparently.

When the user says something that maps to a canonical state-file entry, capture it. Don't pause to ask permission before each one. Each write is small, attributed via git, and trivially reversible.

After a capture, emit a one-line notice in your reply:

```
[recorded D-014: "Use stratified resampling rather than SMOTE for the rare-class case"]
```

If the user says "undo", "drop that", "wait, fix X" → revise (use `git revert <SHA>` for committed captures, edit-in-place for staged ones). If asked how to remove a capture later, point them at the commit SHA the notice referenced.

## Signals to listen for

| Conversational pattern | Likely state-file entry |
|---|---|
| "We decided to …", "let's go with …", "we'll use X" | Decision (`cairn decision add`) |
| "I'll have X by Friday", "Maria can do Y", "I'll take that on" | Action item (`cairn action add`) |
| "Turns out X", "we learned …", "interesting — X surprised me" | Finding (`cairn finding add`) |
| "I wonder if …", "is it true that …", "what about …" | Open question (edit `state/open_questions.yaml`) |
| "Let's try X on a branch" | Branch start (`cairn branch start`) |
| "Shipped" / "done with X" / "that's complete" | Action complete (`cairn action complete`) |
| "Ok let's wrap up", "good place to stop", "I have to go" | Trigger the `debrief` skill |
| "We're abandoning this", "merged that" | Branch close (`cairn branch close`) |

These are heuristics, not rules. When in doubt, capture, and let the user revise — over-capture is recoverable noise, under-capture is lost project memory.

## What NOT to do

- **Don't ask "should I record that?" for every signal.** Just capture and notify. The user picked Cairn because they don't want to be the tracker.
- **Don't try to capture everything.** Small talk, debugging chatter, intermediate tool output don't belong in the substrate. Capture what a future collaborator would want to know.
- **Don't fabricate.** If something is genuinely ambiguous, ask once: *"I'd record this as D-NNN: '<your one-line summary>' — sound right?"* If they say no, drop it.
- **Don't attribute captures to yourself.** Findings, decisions, action items belong to the humans they came from. The CLI handles attribution via the configured git identity.
- **Don't capture on main if the user is on an exploration branch.** Captures land on the current branch by default; the CLI does the right thing.

## The debrief

At natural break points (end of session, end of a working block, before the user logs off), invoke the **debrief** skill — see `skills/debrief/SKILL.md`. It reviews the working conversation and produces a single batched proposal: *"Here are N captures from this session — approve / edit / drop?"*. One round of bulk confirmation rather than per-item interruptions.

## Editing the stance

This file is yours to edit. If the default posture is too noisy or too quiet for how your group works:

- Want less aggressive capture? Tighten the "Signals to listen for" rows or add a "always ask first" clause.
- Want a different vocabulary? Change the patterns to match how your group actually talks.
- Want the agent to capture certain kinds of things only? Narrow the table to those rows.

The schemas in `state/` are the contract; this file is just how the agent rides on top of them.
