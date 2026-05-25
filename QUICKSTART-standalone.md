# Quickstart — standalone

A five-minute path from a clean machine to a working cairn that your Claude Code sessions can read from and write to. Written for a human reader following along at the terminal.

This guide assumes the **standalone** setup: cairn lives on your own machine, you talk to it via Claude Code over a local stdio MCP connection, and you don't yet have access to a group cairn running on a shared HTTP server. If a teammate has already set up a group cairn and given you an endpoint URL and credentials, you want [`QUICKSTART-with-server.md`](QUICKSTART-with-server.md) instead.

**Want your agent to do this for you?** See [`AGENT-BOOTSTRAP.md`](AGENT-BOOTSTRAP.md). Paste that file into a fresh Claude Code session and the agent will install Cairn, scaffold a new cairn, and register you as the first collaborator — pausing for your confirmation at each major step. The agent doc handles both the standalone path (here) and the group-server path; it asks at the start which one applies.

## What you're going to do

1. Install `cairn` with the MCP extra (pipx).
2. Pick a scenario:
   - **Scenario A — Start from scratch:** brand new project, no existing code repo (or you don't want to seed from one yet).
   - **Scenario B — Bootstrap from an existing repo:** the common case — you have a project repo with months/years of history that already encodes decisions and findings.
3. Wire the MCP server into Claude Code (one-time, ever).
4. Pair the project repo with the cairn so agents discover it from cwd.

After this, every Claude Code session anywhere has access to the cairn's MCP tools (`whoami`, `status`, `add_decision`, `add_finding`, `add_action`, `complete_action`, `get_open_questions`, plus a dozen more) without any further setup.

## Step 1 — Install ★

Requires **Python ≥ 3.10** and `git` on PATH. **pipx** is strongly recommended — it puts `cairn` on PATH everywhere without env-activation friction.

```sh
# If pipx isn't already installed:
python -m pip install --user pipx && python -m pipx ensurepath

# Install cairn with the MCP extra:
pipx install 'cairn[mcp] @ git+https://github.com/cranmer/cairn'

# Verify:
cairn --help        # should list init, register, link, mcp, decision, finding, ...
cairn version       # something like 0.0.1.devNN+g<sha>
```

(Cairn is not on PyPI; `pip install cairn` would pull an unrelated package. Always install from the git URL.)

## Step 2 — Configure git identity (one-time) ★

Cairn refuses to commit without a configured git user.

```sh
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```

If they're already set, leave them.

## Step 3 — Choose your scenario

### Scenario A — Start from scratch

For a brand-new project with no existing code repo, or when you'd rather seed the cairn live from conversation rather than bootstrap from history.

```sh
# Scaffold a fresh cairn alongside where your code repo(s) will live:
cd ~/projects                                  # or wherever you keep work
cairn register myproject ./myproject-cairn --init

# Add yourself as the first collaborator:
cd myproject-cairn
cairn collaborator add \
  --id $(whoami) \
  --name "Your Name" \
  --role "what you actually do — 'project lead', 'building the model', etc." \
  --email you@example.com \
  --github your-handle
```

`cairn register --init` does both `cairn init` and registers the cairn with the MCP server in one step. Pick `myproject` as a short handle — that's what MCP tools will receive as the `cairn` parameter (e.g., `add_decision(cairn="myproject", ...)`).

Skip ahead to **Step 4** to wire MCP up.

### Scenario B — Bootstrap from an existing repo

For projects that already have a code repo with accumulated history (README, ADRs, PRs, contributor list). The cairn picks that history up as backdated decisions and findings before live capture starts.

```sh
# Scaffold the cairn alongside the project repo, not inside it:
cd ~/projects                                  # the parent of your code repo
cairn register myproject ./myproject-cairn --init

# Add yourself first (so subsequent writes can be attributed):
cd myproject-cairn
cairn collaborator add \
  --id $(whoami) \
  --name "Your Name" \
  --role "your role" \
  --email you@example.com \
  --github your-handle

# Continue to Step 4 to wire MCP up, THEN open a Claude Code session
# in your project repo and ask the agent to bootstrap. The agent will
# discover and follow the `bootstrap_from_repo` skill — survey the
# repo, draft a single batched proposal of inferred collaborators /
# decisions / findings, get one consent round, then write with
# correctly-backdated dates and structured PR / commit provenance.
```

The bootstrap step itself is an agent action, not a human one. You drive it by asking the agent: *"Bootstrap this cairn from `~/projects/myproject`."* The agent reads the skill and walks the workflow with you.

## Step 4 — Register the MCP server with Claude Code (one-time, ever) ★

```sh
claude mcp add --scope user cairn -- cairn mcp
```

That's it. Same command no matter how many cairns you have — one MCP server serves all of them. Each MCP tool accepts a `cairn` parameter naming which one to operate on; when you have only one registered, that parameter defaults.

The `--scope user` flag is what makes this "one-time, ever": it registers the MCP server for all your Claude Code sessions, not just the current directory. The `--` separator passes the rest of the line to `cairn` rather than letting `claude mcp add` try to parse it.

Confirm:

```sh
claude mcp list           # should show `cairn` in the list
```

**Restart any open Claude Code sessions** so they pick up the new MCP server. New sessions started after this point will have the cairn tools available immediately.

## Step 5 — Link the project repo with the cairn

So that agents working in your project repo discover the right cairn from cwd, without any flag:

```sh
cd ~/projects/myproject                   # your code repo
cairn link --name myproject
```

This writes a small `cairn.toml` at the project repo root naming which cairn (by registry handle) the project pairs with. Agents walk up from cwd, find it, and pass that name to MCP tools transparently.

For Scenario A, your "project repo" may not exist yet; you can run `cairn link` later when it does. For Scenario B, do it now.

## Step 6 — Open a session and check it works

Open Claude Code in your project repo (Scenario B) or the cairn directory (Scenario A) and ask:

> *"What cairn tools do you have?"*

The agent should list the tools (whoami, status, add_decision, etc). Then:

> *"What's the project status?"*

The agent should call the `status` MCP tool. For a fresh cairn it'll return mostly-zero counts plus a `suggested_next` hint about bootstrap if Scenario B applies.

For **Scenario B**, follow up with:

> *"Please bootstrap the cairn from this project repo."*

The agent will follow the bundled `bootstrap_from_repo` skill — survey, propose, consent gate, write with backdated dates + structured provenance.

For **Scenario A**, just start working. The agent will capture decisions, findings, and action items as they come up in conversation (read TRACKING.md inside the cairn to understand the posture).

## What you have now

- A cairn at `~/projects/myproject-cairn/` — your project's shared memory, on disk, in git.
- A pairing file at `~/projects/myproject/cairn.toml` — so agents in the project repo know which cairn to use.
- `cairn` registered as an MCP server in Claude Code — every session can read/write the cairn through ~28 MCP tools.

Anything the cairn knows is in its git history. Anything any collaborator (human or AI) did flows through the same MCP tools you just exercised. Async work compounds.

## What's in a cairn

The default scaffold:

- `PROJECT.md` — three-section overview (Overview, Current focus, Related repositories). Edit via `set_project_overview` / `set_current_focus` / `set_related_repositories` MCP tools.
- `state/decisions.yaml`, `open_questions.yaml`, `action_items.yaml`, `goals.yaml`, `collaborators.yaml` — canonical state. Written via MCP tools or `cairn <verb> add` CLI commands. Don't edit YAML by hand if you can avoid it.
- `knowledge/findings/`, `meetings/`, `literature/`, `provenance/` — accumulating knowledge. Markdown files; findings have YAML frontmatter.
- `skills/<name>/SKILL.md` — bundled agent skills (`orient`, `log-finding`, `log-decision`, `log-action`, `bootstrap_from_repo`, `debrief`, `start-exploration`, `resolve-exploration`, `complete-action`, `search-history`). Read via the `get_skill` MCP tool.
- `explorations/` — tracked alternative lines of inquiry, materialized as git branches.
- `TRACKING.md` — agent-facing posture guide (capture eagerly, debrief at end-of-block, two paths for invoking cairn operations).

## Sharing a cairn with a group

The flow above assumes one researcher with one (or several) cairns on their own machine. If you want a single cairn that several collaborators reach from their own laptops — common for a paper, a working group, a multi-author project — the cairn runs as a long-lived HTTP server somewhere shared, and each collaborator pairs their project repo with the server's URL. That setup has its own choices (where to host, how to credential, how to supervise) and is documented separately in `docs/group-deployment.md`.

## Upgrading later

To pick up the latest:

```sh
pipx install --force 'cairn[mcp] @ git+https://github.com/cranmer/cairn'
```

After upgrading, existing cairns don't auto-receive new bundled skills. Run inside each cairn:

```sh
cairn skills sync         # copies any newly-bundled skills into this cairn
```

`sync` is non-destructive by default — it only copies skills you don't have. Pass `--force` to also overwrite ones you've hand-edited (rarely what you want).

## Where to go next

- `ARCHITECTURE.md` — design document, the principles, the build path.
- `USER_STORIES.md` — testable user stories. The primary specification.
- `docs/decisions/` — ADRs locking in design choices.
- `docs/open-questions.md` — unresolved design tensions awaiting ADRs.
- `docs/index.html` — polished overview for sharing with colleagues; also the GitHub Pages landing page.
- `docs/group-deployment.md` — running a cairn as a shared HTTP service for multi-collaborator projects.
