# {{cookiecutter.project_name}}

*Agent orientation file. Short by design — agents read this first.*

## Overview

TODO: One or two paragraphs describing what this project is about, who's on it, and what stage it's in.

## Where things live

- `state/decisions.yaml` — canonical decisions, with author and timestamp.
- `state/open_questions.yaml` — questions the group is working through.
- `state/action_items.yaml` — assignments with due dates.
- `state/goals.yaml` — project milestones.
- `state/collaborators.yaml` — people (and AI agents) on the project.
- `knowledge/meetings/` — one markdown file per meeting (`YYYY-MM-DD.md`).
- `knowledge/findings/` — logged findings, dated and attributed.
- `knowledge/literature/` — papers and notes.
- `knowledge/provenance/` — reproducibility artifacts (RO-Crate, ASTRA, ARA, etc.).
- `skills/` — procedural skills available to agents working in this cairn.
- `branches/README.md` — index of active branches.
- `TRACKING.md` — agent-facing posture guide: how the agent should capture state from conversation so the user doesn't have to invoke commands by hand.

## Current focus

TODO: What is the group actively working on this month? List 2–4 items, each linked to a goal or open question by ID.

## How to contribute

- Humans: edit files directly and commit. Use `cairn` CLI helpers (`cairn collaborator add`, `cairn decision add`, etc.) when convenient — but you shouldn't have to invoke them by hand if you're working with an agent (see below).
- Agents: read this file, then `state/collaborators.yaml` to know who you're talking to, then `TRACKING.md` to know how to track for the user without them having to be explicit about every capture. Use the skills in `skills/` for common workflows. The `debrief` skill at session end catches anything that slipped through live capture.

## Related repositories

This cairn is *not* the project's code repo. Most research projects already have one or more git repos for their code / data / paper — the cairn sits alongside them, holding shared memory (decisions, questions, findings, action items) that doesn't fit naturally inside any of them.

TODO: list the project's working repos here, one per line, with a one-sentence description of what each contains. For example:

- `cranmer/mutual-info-analysis` — main analysis pipeline (R + Python).
- `cranmer/mutual-info-paper` — LaTeX source for the manuscript.
- `cranmer/mutual-info-data` — preprocessed datasets and DVC pointers.

Structured cross-references from findings/decisions back to specific commits in these repos are future work; for now, paste commit SHAs or URLs into the relevant fields freely.

## Project metadata

- **GitHub org**: {{cookiecutter.github_org}}

(People on the project — and how they describe their own roles — live in `state/collaborators.yaml`, not here.)
