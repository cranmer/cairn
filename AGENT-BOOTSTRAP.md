# Bootstrap a cairn — instructions for an agent

**You** (Claude Code, the agent reading this) are being asked to help the user set up cairn — a git-native shared memory for a research project — on their machine. The user has pasted this file to you. Follow these instructions; **pause for confirmation at the ★ marks** before taking the listed action. Do not skip ahead.

The setup has two main shapes:

- **Standalone:** the user is creating a new personal cairn on their own machine; Claude Code talks to it over a local stdio MCP connection. Most users start here.
- **Joining a group server:** a cairn is already running on a shared HTTP server; you're hooking the user's local machine to it. The cairn exists already; you're not creating it.

You don't have to know which one applies at the start — Step 4 below is the branching point. Read the file end-to-end first; the steps are short and the two branches diverge cleanly.

If the user has already created a cairn and just wants you to orient inside it, this file is the wrong one — point them at the cairn's `TRACKING.md` (inside the cairn) and ask what they'd like to do next. If the user is the one *setting up the group server itself* (rather than joining one), point them at [`docs/group-deployment.md`](docs/group-deployment.md) — that's an operations doc, not a per-user setup script.

## Capture this early — you'll need it

Before you `cd` anywhere or run anything substantive, **capture two facts**:

- `pwd` — your starting working directory. Mode reporting at the end depends on this.
- Whether the user's project repo (if any) already exists on disk. Note its path.

## Steps 1–3 are the same regardless of which branch the user takes

### Step 1 — Verify prerequisites

Run both, in parallel:

```sh
python --version    # need >= 3.10
git --version       # any recent version
```

If either is missing or below the required version, **stop** and tell the user what to install. Do not install Python or git for them.

### Step 2 — Install Cairn ★

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

### Step 3 — Confirm git identity ★

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

## Step 4 — Branching point: standalone or joining a server? ★

Ask the user:

> *"Two shapes of setup. (1) **Standalone** — you're setting up cairn on this machine for a personal project; the cairn lives in a local git repo here. (2) **Joining a group server** — a teammate has already set up a cairn on a shared HTTP server somewhere, and you have an endpoint URL and a bearer token from them. Which fits?"*

If they pick **standalone** → continue to **Step 4S** below.

If they pick **joining a group server** → skip ahead to **Step 4J** below.

If they say "I want to set up a group server for my team" — that's neither of these flows; point them at [`docs/group-deployment.md`](docs/group-deployment.md) and stop. Don't try to drive a server deployment from this script; spinning up a long-lived HTTP server is an ops decision that needs a real plan.

---

## Standalone track — Steps 4S–10S

Use this track if the user chose standalone in Step 4.

### Step 4S — Choose scenario (A vs B) ★

Ask the user:

> *"Within the standalone setup, two ways to start. (A) **Start from scratch** — a brand-new cairn with no existing project repo to seed from. (B) **Bootstrap from an existing repo** — you have a project repo with months or years of history (README, ADRs, PR descriptions, contributor list) and want the cairn to pick that up as backdated decisions and findings before live capture begins. Which fits?"*

Also collect:

- **Project name** (short, kebab-case if possible — becomes the cairn directory name and the MCP registry handle).
- **Parent directory** — where the cairn will live (defaults to `~/projects/` or wherever they keep work).
- **For Scenario B**: the absolute path of the project repo to bootstrap from.

Echo all collected values back, then proceed.

### Step 5S — Scaffold + register the cairn ★

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

### Step 6S — Register the user as the first collaborator ★

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

### Step 7S — Register the MCP server with Claude Code ★

```sh
claude mcp add --scope user cairn -- cairn mcp
```

This is **one-time, ever** — the same command regardless of how many cairns the user has. One MCP server serves all of them.

Confirm:

```sh
claude mcp list   # `cairn` should appear
```

Tell the user explicitly:

> *"I've registered the cairn MCP server with Claude Code. To pick up the change in any currently-running Claude Code sessions, you'll need to restart them. New sessions started from this point will have the cairn tools available automatically."*

### Step 8S — Pair the project repo (optional, recommended for Scenario B)

If the user has a project repo and wants agents working in it to discover the cairn automatically:

```sh
cd <path-to-project-repo>
cairn link --name <project-name>
```

This writes a small `cairn.toml` at the project repo's root naming the registry handle. Agents walk up from cwd, find it, and pass that name to MCP tools transparently — no `cd` needed.

### Step 9S — Drive the bootstrap (Scenario B only)

If the user picked **Scenario B**, the cairn now exists but is empty. **You** drive the bootstrap from this same session:

1. Tell the user: *"Now I'll bootstrap the cairn from `<project-repo-path>`. I'll survey its README, docs, git history, and PR descriptions; draft a single batched proposal of inferred collaborators, decisions, findings, and open questions; and get one consent round from you before any writes. Sound right?"*

2. Read the bundled `bootstrap_from_repo` skill — either by reading `<cairn-path>/skills/bootstrap_from_repo/SKILL.md` directly, or by calling the MCP tool `get_skill(name="bootstrap_from_repo")` if your session has the MCP server connected.

3. Follow that skill's procedure. The skill explicitly covers: surveying order, type classification (decision / finding / question / action), the batched-proposal consent gate, backdating with the `date` parameter, structured PR / commit provenance via `source_prs` and `source_commits`, the *ambiguous authorship* pattern (use a `repo-history` collaborator with `type="unknown"` for observations no single human authored), and the summarize-and-stop closing.

4. **Stop after the bootstrap completes.** The user will direct what comes next.

### Step 10S — When you're done (standalone)

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

---

## Group-server track — Steps 4J–9J

Use this track if the user chose joining a group server in Step 4.

### Step 4J — Collect the four facts ★

Ask the user:

> *"To join the group cairn I need four things from you (or from whoever set up the server): (1) the endpoint URL — something like `https://cairn.lab.example.org/mcp`; (2) the cairn handle — a short name like `coral-bleach` that identifies which cairn on the server; (3) the bearer token; (4) the collaborator id you'll write under. Have you been given all four?"*

If any are missing, ask the user to get them from the team. **Do not invent values.** In particular:

- Do not pick a collaborator id yourself. The server-side admin must have added the user to `state/collaborators.yaml`, and the id has to match. If the user is unsure, have them confirm with the team before continuing.
- Do not guess at the cairn handle. The `cairn link` probe will fail unhelpfully if the handle isn't a real cairn on the server.

Echo all four back to the user and confirm before continuing.

### Step 5J — Store the bearer token ★

Persist it to the credentials file (not on the command line, where it would land in shell history):

```sh
mkdir -p ~/.config/cairn
cat > ~/.config/cairn/credentials.toml <<EOF
[endpoints."<endpoint-url>"]
token = "<the-token>"
EOF
chmod 600 ~/.config/cairn/credentials.toml
```

Verify:

```sh
ls -l ~/.config/cairn/credentials.toml   # mode should be -rw-------
```

### Step 6J — Pair the project repo ★

If the user has a project repo (likely yes), pair it:

```sh
cd <path-to-project-repo>
cairn link --endpoint <endpoint-url> --name <cairn-handle>
```

The `link` command runs a connectivity probe before writing the `cairn.toml`. Common probe failures:

- `could not reach <endpoint>`: network down, endpoint wrong, server isn't running.
- HTTP 401/403: token wrong or expired; go back to Step 5J.
- Probe succeeds but the cairn handle is wrong: caught at Step 7J with `cairn 'X' is not registered`.

Surface the exact error to the user — don't try `--no-probe` to skip the check unless they explicitly ask.

Verify:

```sh
cat cairn.toml   # should show endpoint + name lines, no token
```

### Step 7J — Smoke test with a real write ★

```sh
cairn finding add --author <collaborator-id> \
  --title "Joining the cairn" \
  --body "Smoke test from a new client to confirm the wire works."
```

This is a **real write**. Tell the user so honestly: the server now holds a finding attributed to them, visible to everyone else on the team. The CLI prints the resulting filename and the server-resolved cairn name.

Error modes to watch for:

- **HTTP 401**: token wrong or expired. Confirm with the user, re-run Step 5J with a correct token.
- **`unknown author '<id>' in this cairn`**: the team hasn't added the user as a collaborator yet. **Stop here** and tell the user to ask. Do not try to add them yourself — that requires server-side access this script doesn't have.
- **`could not reach`**: server went down or network changed between Step 6J and now.

### Step 8J — Register the remote MCP with Claude Code ★

```sh
claude mcp add --scope user --transport http cairn-remote <endpoint-url>
```

If the user's Claude Code version doesn't accept `--transport http`, check `claude mcp add --help` for their version's HTTP/SSE option, or fall back to editing `~/.claude.json` directly.

Confirm:

```sh
claude mcp list   # `cairn-remote` should appear
```

Tell the user explicitly:

> *"I've registered the remote cairn MCP with Claude Code. To pick up the change in any currently-running Claude Code sessions, restart them. New sessions from this point will have the cairn's tools available automatically."*

### Step 9J — When you're done (group-server)

Report **honestly**:

1. **The user is paired with a remote cairn at** `<endpoint-url>` (handle: `<cairn-handle>`).
2. **Their bearer token lives at** `~/.config/cairn/credentials.toml` (mode 0600, not committed).
3. **They can write from the CLI or from any Claude Code session in the paired project repo.** Writes show up immediately for the other collaborators.
4. **You did NOT add them as a collaborator** — that was done by the server admin before this session started.
5. **The smoke-test finding from Step 7J is now in the cairn**. If they want to clean it up, the server admin can remove the file directly; there's no client-side delete.

Then stop. The user will direct what comes next.

---

## What you should *not* do — applies to both tracks

- Do not commit on the user's behalf without showing them the proposed commit message first (after this bootstrap is complete; during bootstrap, `cairn` and the MCP tools handle attribution).
- Do not install global pip packages without confirming the environment.
- Do not run `git config --global` to change values the user already has set.
- Do not create more than one cairn in this session. One project = one cairn.
- Do not ask the user to run cairn CLI commands. You have the CLI and the MCP tools — use them on the user's behalf.
- Do not start a long-lived HTTP MCP server on the user's behalf. If they want a group-shared cairn, hand off to [`docs/group-deployment.md`](docs/group-deployment.md) instead of improvising.

**Standalone-only:**
- Do not claim "Mode A / server mode" if the user's initial cwd was their project repo. The mode is set the moment Claude Code launched, not by where you `cd` during bootstrap.

**Group-server-only:**
- Do not run `cairn init` or `cairn register --init` — the cairn exists remotely; creating a new local cairn here would conflict.
- Do not run `cairn collaborator add` — adding collaborators is a server-side operation. If the user isn't already a collaborator, stop and ask them to fix it server-side.
- Do not write the bearer token into `cairn.toml`. Credentials live separately in `~/.config/cairn/credentials.toml`.
- Do not commit the credentials file.
- Do not invent a collaborator id, an endpoint URL, a cairn handle, or a token. If any is missing, stop and ask the user.

## If something fails

**Common to both tracks:**

- **`cairn` command not found after install**: pipx didn't put it on PATH. Tell the user; offer the absolute path (`~/.local/bin/cairn …`).
- **`cairn init` errors with "no git user identity configured"**: go back to Step 3; do not invent values.
- **`claude mcp add` not available**: the user's Claude Code may be older than the `mcp add` CLI feature. Fall back to editing `~/.claude.json` directly.
- **MCP tools not visible in a follow-up session**: confirm `claude mcp list` shows the relevant server, then the user needs to restart Claude Code (not just clear context — a true session restart).
- **Any other error**: stop, show the user the exact error, ask how to proceed. Do not edit state files by hand to "fix" things without confirmation.

**Standalone-only:**

- **`cairn register --init` errors with "refusing to overwrite"**: a directory with that name already exists. Ask the user whether to pick a new name or pass `--force` (which deletes the existing directory; warn first).

**Group-server-only:**

- **`cairn link` errors with "could not reach"**: surface the exact error; common causes are wrong endpoint, network issue, or server down.
- **HTTP 401/403** at any step: token wrong or expired. Re-collect from the user, redo Step 5J.
- **First write returns `unknown author`**: the team hasn't added the user yet. Stop, ask them to fix server-side, retry.

## Upgrading cairn later (after this bootstrap is done)

To pick up the latest:

```sh
pipx install --force 'cairn[mcp] @ git+https://github.com/cranmer/cairn'
```

**Standalone:** existing cairns don't auto-receive new bundled skills after an upgrade. Run inside the cairn:

```sh
cairn skills sync   # non-destructive; only copies skills the cairn doesn't have
```

**Group-server:** bundled skills live in the cairn on the server, not on the user's machine — they get updated by whoever runs the server, not from here. `cairn skills sync` is a server-side operation; the user does not run it.

That's it. The user can now describe what they want to do next, and you should pick the right approach — usually nothing more than listening and capturing transparently as the work happens.
