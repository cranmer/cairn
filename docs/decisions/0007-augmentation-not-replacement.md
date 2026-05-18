# 0007 — Augmentation, not replacement

## Context

Cairn could have been (and many tools in this space are) **replacement systems**: new chat platforms, new project-management UIs, new "knowledge graphs" with proprietary data models, new agent harnesses with their own workflow vocabularies. Each requires the user to learn a new ritual, switch contexts, and produce material in a foreign shape. Adoption fails not because the idea is bad but because the tax of "do your normal work *and* feed our tool" exceeds the marginal value.

The thing missing in most of those tools isn't features — it's a posture. The substrate-as-specification principle (ADR-0005, and ARCHITECTURE.md §Architectural Principles) addresses the *storage* axis of that question: no proprietary backend, everything is files in git. But there's a parallel question on the *workflow* axis that has never been explicitly named: what does Cairn ask of the people who use it?

Real usage data — UX experiments running an agent through `AGENT-BOOTSTRAP.md` and follow-on work in Mode B against an actual project repo (StellaForge) — surfaced that the answer matters concretely and frequently. The agent, taking its lead from the bootstrap doc, defaulted to *cairn-specific* concepts (cairn branches, "open a separate session inside the cairn for cairn work," cd-into-the-cairn-for-every-command) instead of project-native concepts (the user's git branches, the user's existing session, project-repo defaults). Each was a small instance of "Cairn is asking you to change how you work." Each was friction.

Naming the principle makes those judgments explicit instead of accidental.

## Decision

**Augmentation, not replacement.** Cairn does not redirect how collaborators work. They keep using their normal tools — git, Zoom, Slack, email, paper, conversation — at their normal rhythm. An agent listens in those native channels and writes structured notes into the cairn as a side effect.

The agent's role is **facilitator, not stenographer**. Like a thoughtful human note-taker at a meeting, an agent may occasionally ask focused clarifying questions in service of accurate capture: *"Is this the decision wording?"*, *"Should I file this as an action — assign to whom?"*, *"Looks like Q-005 is resolved; close it?"* These are the questions a good collaborator asks. They are **not** the questions a tool asks: agents do not say *"please run `cairn decision add --text…`"*, do not propose new rituals or session-switching, and do not micro-confirm every capture inline (debrief at end-of-block instead).

**The test, when designing or implementing any feature:** would a thoughtful new collaborator joining the project naturally be doing this same thing? If yes, an agent should do it. If it requires the user to learn a new verb, adopt a new tool, or perform a new ceremony, it violates this principle.

This pairs with the existing **substrate-as-specification** principle:

- Substrate-as-specification answers *where state lives* — in files, in git, in the user's normal storage. No proprietary system.
- Augmentation-not-replacement answers *where work happens* — in the user's normal channels, at their normal rhythm. No proprietary workflow.

Together they describe what Cairn is for, and what other tools in this space typically aren't.

## Consequences

- **TRACKING.md is this principle applied to the agent's in-session conversation.** Capture eagerly during conversation; the user shouldn't have to invoke CLI commands by hand. ADR-0007 names the principle TRACKING.md was already operationalizing.

- **US-P-07 (meeting import) is this principle applied to meetings.** A Zoom transcript or Otter export is processed by an agent into cairn notes + staged decisions; the meeting attendees did not change how they met. Future capture for Slack threads, email exchanges, paper-and-pencil sessions falls in the same shape.

- **Debrief over per-item confirmation.** The agent's questions cost more than its captures — each clarifying question is an interruption, each silent capture is free. Bias toward capture-then-summarize at the end of a block (the `debrief` skill is the existing mechanism); reserve clarifying questions for genuinely ambiguous cases where wrong capture would be worse than asking.

- **Client mode is primary (ADR-0008).** Day-to-day work happens in client mode — the user in their project repo, in a Zoom call, in a Slack thread, with an agent listening and capturing transparently. Server mode (sessions opened inside the cairn for maintenance and curation) is real but secondary. This reverses the earlier "Mode A v0" framing from ADR-0005.

- **Default verb interpretations follow native conventions** (ADR-0008). In client mode, "let's create a branch" defaults to a project-repo git branch (the git-native answer), not a cairn-internal exploration. Cairn explorations exist for cases where they add value beyond what git branches give, but they are not the default.

- **AGENT-BOOTSTRAP.md and bundled SKILL.md files need a posture audit.** Anywhere they tell the agent to invoke a cairn-specific ritual where a native action would suffice, that's a principle violation. Followed up in a subsequent PR (R3).

- **Future features get measured against the principle.** Speculative additions ("a cairn dashboard," "a cairn chat UI," "a cairn task-board view") face the test: do they require the user to leave their normal channels? If yes, the design is wrong, even if the feature is appealing.

- **Trigger for revisiting:** a use case where transparent capture in native channels is genuinely impossible without an interruption that would feel imposing, *and* the user-research signal supports paying that cost. Such cases are expected to be rare; treat them as exceptions, not new defaults.
