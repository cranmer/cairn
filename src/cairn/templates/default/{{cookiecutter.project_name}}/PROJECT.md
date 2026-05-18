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

## Current focus

TODO: What is the group actively working on this month? List 2–4 items, each linked to a goal or open question by ID.

## How to contribute

- Humans: edit files directly and commit. Use `cairn` CLI helpers (`cairn collaborator add`, `cairn decision add`, etc.) when convenient.
- Agents: read this file, then `state/collaborators.yaml` to know who you're talking to. Use the skills in `skills/` for common workflows. Don't write to canonical state on behalf of a user without their confirmation.

## Project metadata

- **GitHub org**: {{cookiecutter.github_org}}

(People on the project — and how they describe their own roles — live in `state/collaborators.yaml`, not here.)
