# Bootstrap a cairn — instructions for an agent

**You** (Claude Code, the agent reading this) are being asked to set up a new *cairn* — a git-native shared memory for a research project — on the user's machine. The user has pasted this file to you. Follow these instructions; **pause for confirmation at the ★ marks** before taking the listed action. Do not skip ahead.

If the user has already created a cairn and just wants you to orient inside it, this file is the wrong one — point them at the cairn's `TRACKING.md` (inside the cairn) and ask what they'd like to do next.

This is the agent-driven companion to `QUICKSTART.md` (the human-driven version). The two flows produce the same end state. Read this file end-to-end before starting; the steps are short.

## Capture this early — you'll need it

Before you `cd` anywhere or run anything substantive, **capture two facts**:

- `pwd` — your starting working directory. Mode reporting at the end depends on this.
- Whether the user's project repo (if any) already exists on disk. Note its path.

## What you're going to do

1. Verify Python ≥ 3.10 and `git` on PATH.
2. Install `cairn` with the MCP extra via pipx.
3. Confirm or set the user's git identity.
4. Decide: **start from scratch** (no source repo to bootstrap from) or **bootstrap from an existing repo** (most common — months/years of history to seed from).
5. Scaffold and register the cairn.
6. Register yourself (the user) as the first collaborator.
7. Wire the MCP server into Claude Code (one-time, ever).
8. Pair the project repo with the cairn (optional but recommended).
9. Hand off to the user — and, if bootstrapping, drive the bootstrap workflow yourself.

## Step 1 — Verify prerequisites

Run both, in parallel:

```sh
python --version    # need >= 3.10
git --version       # any recent version
```

If either is missing or below the required version, **stop** and tell the user what to install. Do not install Python or git for them.

## Step 2 — Install Cairn ★

> **UX note for you (the agent).** Your shell tool starts a fresh process for each command — `conda activate` or `source venv/bin/activate` in one tool call does NOT persist to the next. **Use pipx.** It puts `cairn` on the user's PATH everywhere with no activation friction.

If `pipx` isn't already installed:

```sh
python -m pip install --user pipx && python -m pipx ensurepath
# (the user may need to restart their shell or `source ~/.bashrc` after ensurepath)
```

Then install cairn with the MCP extra:

```sh
pipx install 'cairn[mcp] @ git+https://github.com/cranmer/cairn'
```

(Cairn is **not** on PyPI. `pip install cairn` would pull an unrelated package — do not use it.)

Verify:

```sh
cairn --help        # should list init, register, link, mcp, decision, finding, ...
cairn version       # something like 0.0.1.devNN+g<sha>
```

If `cairn --help` doesn't resolve after install, the user's `~/.local/bin` probably isn't on PATH. Tell them; offer to use `~/.local/bin/cairn` as an absolute path for the rest of this session.

## Step 3 — Confirm git identity ★

Run:

```sh
git config --global user.name
git config --global user.email
```

If both return values: echo them back to the user and ask if they should be used as the cairn's identity. If they say yes, proceed. If no, ask for the right values and set them:

```sh
git config --global user.name  "Their Name"
git config --global user.email "they@example.com"
```

If either is missing: ask the user for the value and set it. **Do not invent values.** The commit author must be the real human — cairn's substrate-as-truth principle requires it.

## Step 4 — Choose scenario ★

Ask the user:

> *"Two ways to start: (A) **start from scratch** — a brand-new cairn with no existing project repo to seed from, or (B) **bootstrap from an existing repo** — you have a project repo with months or years of history (README, ADRs, PR descriptions, contributor list) and want the cairn to pick that up as backdated decisions and findings before live capture begins. Which fits?"*

Also collect:

- **Project name** (short, kebab-case if possible — becomes the cairn directory name and the MCP registry handle).
- **Parent directory** — where the cairn will live (defaults to `~/projects/` or wherever they keep work).
- **For Scenario B**: the absolute path of the project repo to bootstrap from.

Echo all collected values back, then proceed.

## Step 5 — Scaffold + register the cairn ★

```sh
cd <parent-directory>
cairn register <project-name> ./<project-name>-cairn --init
```

`cairn register --init` does `cairn init` followed by registry registration in one step. The cairn ends up at `<parent-directory>/<project-name>-cairn/`, alongside any project repos, never inside them.

Verify:

```sh
cd <project-name>-cairn
ls -la            # at minimum: PROJECT.md, README.md, TRACKING.md, .gitignore,
                  # .cairn, .claude/, state/, knowledge/, skills/, explorations/
git log --oneline # one commit "Initial commit: scaffold cairn '<name>'"
cairn registered  # confirm <project-name> appears
```

If the scaffold output mentions disabling commit signing for this cairn (because `commit.gpgsign=true` globally but no `user.signingkey` is configured), that's expected and benign — it just makes future manual `git commit` calls in the cairn work without signing failures.

## Step 6 — Register the user as the first collaborator ★

Ask:

- **Collaborator id** — short, kebab-case, lowercase (e.g., `kyle`, `maria-s`). Used in attributions and cross-references throughout the cairn.
- **Role** — what they actually *do* on this project. Bias toward activity-based descriptions ("designing generative models", "running ablation experiments", "writing the introduction") over titles ("PI", "postdoc", "professor"). If they offer a title, accept it.
- **Email** — pre-fill from `git config --get user.email` and confirm. The `orient` skill matches the current git user against collaborator emails; without this every future session has to ask.
- Optional: GitHub handle, expertise tags, current focus.

Then:

```sh
cairn collaborator add \
  --id <chosen-id> \
  --name "<Their Full Name>" \
  --role "<role>" \
  --email <they@example.com> \
  [--github <handle>] \
  [--expertise <topic> --expertise <topic>] \
  [--current-focus "<short description>"]
```

Verify:

```sh
cat state/collaborators.yaml   # the new entry should be there
git log --oneline               # "Add collaborator '<id>'"
```

## Step 7 — Register the MCP server with Claude Code ★

```sh
claude mcp add cairn -- cairn mcp
```

This is **one-time, ever** — the same command regardless of how many cairns the user has. One MCP server serves all of them (per ADR-0010).

Confirm:

```sh
claude mcp list   # `cairn` should appear
```

Tell the user explicitly:

> *"I've registered the cairn MCP server with Claude Code. To pick up the change in any currently-running Claude Code sessions, you'll need to restart them. New sessions started from this point will have the cairn tools available automatically."*

## Step 8 — Pair the project repo (optional, recommended for Scenario B)

If the user has a project repo and wants agents working in it to discover the cairn automatically:

```sh
cd <path-to-project-repo>
cairn link --name <project-name>
```

This writes a small `cairn.toml` at the project repo's root naming the registry handle. Agents walk up from cwd, find it, and pass that name to MCP tools transparently — no `cd` needed.

## Step 9 — Drive the bootstrap (Scenario B only)

If the user picked **Scenario B**, the cairn now exists but is empty. **You** drive the bootstrap from this same session:

1. Tell the user: *"Now I'll bootstrap the cairn from `<project-repo-path>`. I'll survey its README, docs, git history, and PR descriptions; draft a single batched proposal of inferred collaborators, decisions, findings, and open questions; and get one consent round from you before any writes. Sound right?"*

2. Read the bundled `bootstrap_from_repo` skill — either by reading `<cairn-path>/skills/bootstrap_from_repo/SKILL.md` directly, or by calling the MCP tool `get_skill(name="bootstrap_from_repo")` if your session has the MCP server connected.

3. Follow that skill's procedure. The skill explicitly covers: surveying order, type classification (decision / finding / question / action), the batched-proposal consent gate, backdating with the `date` parameter, structured PR / commit provenance via `source_prs` and `source_commits`, the *ambiguous authorship* pattern (use a `repo-history` collaborator with `type="unknown"` for observations no single human authored), and the summarize-and-stop closing.

4. **Stop after the bootstrap completes.** The user will direct what comes next.

## Step 10 — When you're done

Report **honestly** about what just happened. Key facts to convey:

1. **The cairn lives at** `<absolute-path>`. It's a sibling of the project repo (if any), not nested inside.
2. **Mode determination**: was the user's *initial* cwd (the one you captured at the very start) the same as the cairn directory you just `cd`'d into?
   - If **yes** → this session is in **server mode**; the cairn's SessionStart hook fired and `cairn status` ran automatically.
   - If **no** (the initial cwd was elsewhere — typically the user's project repo) → this session is in **client mode**; the hook did not fire. You can still run cairn commands by `cd`-ing or via MCP, but be honest: the auto-orient didn't happen.
3. **What the user should expect from here**:
   - Future Claude Code sessions opened *anywhere* will have the cairn MCP tools available (after they restart any open ones to pick up the `claude mcp add` change).
   - Cairn captures happen as a side effect of conversation — they shouldn't have to learn new commands. The `TRACKING.md` posture guide inside the cairn explains the agent's role.
   - For Scenario A users: just start working. Mention findings, decisions, action items as they come up — the agent will capture them.
   - For Scenario B users: the bootstrap is now in the cairn's history with backdated entries and structured provenance.

Then stop. The user will direct the next step.

## What you should *not* do

- Do not commit on the user's behalf without showing them the proposed commit message first (after this bootstrap is complete; during bootstrap, `cairn` and the MCP tools handle attribution).
- Do not install global pip packages without confirming the environment.
- Do not run `git config --global` to change values the user already has set.
- Do not create more than one cairn in this session. One project = one cairn.
- Do not claim "Mode A / server mode" if the user's initial cwd was their project repo. The mode is set the moment Claude Code launched, not by where you `cd` during bootstrap.
- Do not ask the user to run cairn CLI commands. You have the CLI and the MCP tools — use them on the user's behalf.

## If something fails

- **`cairn` command not found after install**: pipx didn't put it on PATH. Tell the user; offer the absolute path (`~/.local/bin/cairn …`).
- **`cairn init` errors with "no git user identity configured"**: go back to Step 3; do not invent values.
- **`cairn register --init` errors with "refusing to overwrite"**: a directory with that name already exists. Ask the user whether to pick a new name or pass `--force` (which deletes the existing directory; warn first).
- **`claude mcp add` not available**: the user's Claude Code may be older than the `mcp add` CLI feature. Fall back to editing `~/.claude.json` directly to add `{"mcpServers": {"cairn": {"command": "cairn", "args": ["mcp"]}}}`.
- **MCP tools not visible in a follow-up session**: confirm `claude mcp list` shows `cairn`, then the user needs to restart Claude Code (not just clear context — a true session restart).
- **Any other error**: stop, show the user the exact error, ask how to proceed. Do not edit state files by hand to "fix" things without confirmation.

## Upgrading cairn later (after this bootstrap is done)

Cairn is pre-1.0 and changes land on `main`. To pick up the latest:

```sh
pipx install --force 'cairn[mcp] @ git+https://github.com/cranmer/cairn'
```

After upgrading, existing cairns don't auto-receive new bundled skills. Run inside the cairn:

```sh
cairn skills sync   # non-destructive; only copies skills the cairn doesn't have
```

That's it. The user can now describe what they want to do next, and you should pick the right approach — usually nothing more than listening and capturing transparently as the work happens.
