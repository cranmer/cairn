# Join a group cairn — instructions for an agent

**You** (Claude Code, the agent reading this) are being asked to help the user join a cairn that already exists on a shared HTTP server. The cairn isn't being created here — someone on the team set it up; you're hooking the user's local machine to it.

Pause for confirmation at the ★ marks before taking the listed action. Do not skip ahead.

If the user wants to create a brand-new personal cairn instead, this file is the wrong one — point them at [`AGENT-BOOTSTRAP.md`](AGENT-BOOTSTRAP.md). If the user is the one *setting up* the group server, this file is also wrong — point them at `docs/group-deployment.md`.

## Capture this early

Before you `cd` anywhere or run anything substantive:

- `pwd` — your starting working directory. Mode reporting at the end depends on this.
- Whether the user's project repo (if any) already exists on disk. Note its path.

## What you're going to do

1. Verify Python ≥ 3.10 and `git` on PATH.
2. Install `cairn` via pipx.
3. Confirm or set the user's git identity.
4. Collect the four facts you need from the user (or the team running the cairn): endpoint URL, cairn handle, bearer token, collaborator id. Confirm the user is already registered server-side.
5. Store the bearer token in `~/.config/cairn/credentials.toml`.
6. Pair the user's project repo with the remote cairn.
7. Smoke-test the connection with a real write.
8. Register the remote MCP server with Claude Code.
9. Hand off honestly.

## Step 1 — Verify prerequisites

Run both, in parallel:

```sh
python --version    # need >= 3.10
git --version       # any recent version
```

If either is missing, **stop** and tell the user what to install. Do not install Python or git for them.

## Step 2 — Install Cairn ★

> **UX note for you (the agent).** Your shell tool starts a fresh process for each command — `conda activate` or `source venv/bin/activate` in one tool call does NOT persist to the next. **Use pipx.**

```sh
# If pipx isn't already installed:
python -m pip install --user pipx && python -m pipx ensurepath

# Install:
pipx install 'cairn[mcp] @ git+https://github.com/cranmer/cairn'
```

(Cairn is **not** on PyPI. `pip install cairn` would pull an unrelated package — do not use it.)

Verify:

```sh
cairn --help
cairn version
```

If `cairn --help` doesn't resolve, the user's `~/.local/bin` probably isn't on PATH. Tell them; offer absolute paths for the rest of this session.

## Step 3 — Confirm git identity ★

```sh
git config --global user.name
git config --global user.email
```

If both return values: confirm with the user that they're correct for cairn use, and that the email matches the collaborator id they've been assigned on the server. If either is missing, ask the user for the value and set it. **Do not invent values.**

## Step 4 — Collect the four facts ★

Ask the user:

> *"To join the group cairn I need four things from you (or from whoever set up the server): (1) the endpoint URL — something like `https://cairn.lab.example.org/mcp`; (2) the cairn handle — a short name like `coral-bleach` that identifies which cairn on the server; (3) the bearer token; (4) the collaborator id you'll write under. Have you been given all four?"*

If any are missing, ask the user to get them from the team. **Do not invent values.** In particular:

- Do not pick a collaborator id yourself. The server-side admin must have added the user to `state/collaborators.yaml`, and the id has to match. If the user is unsure, have them confirm with the team before continuing.
- Do not guess at the cairn handle. The CLI's `cairn link` probe will fail unhelpfully if the handle isn't a real cairn on the server.

Echo all four back to the user and confirm before continuing.

## Step 5 — Store the bearer token ★

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

## Step 6 — Pair the project repo ★

If the user has a project repo (likely yes), pair it:

```sh
cd <path-to-project-repo>
cairn link --endpoint <endpoint-url> --name <cairn-handle>
```

The `link` command runs a connectivity probe before writing the `cairn.toml`. Common probe failures and what they mean:

- `could not reach <endpoint>`: network down, endpoint wrong, server isn't running.
- HTTP 401/403: token wrong or expired; go back to Step 5.
- Probe succeeds but the cairn handle is wrong: caught when the first write hits Step 7 with `cairn 'X' is not registered`.

Surface the exact error to the user — don't try `--no-probe` to skip the check unless they explicitly ask.

Verify:

```sh
cat cairn.toml   # should show endpoint + name lines, no token
```

## Step 7 — Smoke test with a real write ★

```sh
cairn finding add --author <collaborator-id> \
  --title "Joining the cairn" \
  --body "Smoke test from a new client to confirm the wire works."
```

This is a **real write**. Tell the user so honestly: the server now holds a finding attributed to them, visible to everyone else on the team. The CLI prints the resulting filename and the server-resolved cairn name.

Error modes to watch for, and how to respond:

- **HTTP 401**: token wrong or expired. Confirm with the user, re-run Step 5 with a correct token.
- **`unknown author '<id>' in this cairn`**: the team hasn't added the user as a collaborator yet. **Stop here** and tell the user to ask. Do not try to add them yourself — that requires server-side access this script doesn't have.
- **`could not reach`**: server went down or network changed between Step 6 and now.

## Step 8 — Register the remote MCP with Claude Code ★

So the user's Claude Code sessions can reach the cairn's MCP tools directly:

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

## Step 9 — Hand off

Report **honestly** about what happened. Key facts to convey:

1. **The user is paired with a remote cairn at** `<endpoint-url>` (handle: `<cairn-handle>`).
2. **Their bearer token lives at** `~/.config/cairn/credentials.toml` (mode 0600, not committed).
3. **They can write from the CLI or from any Claude Code session in the paired project repo.** Writes show up immediately for the other collaborators.
4. **You did NOT add them as a collaborator** — that was done by the server admin before this session started.
5. **The smoke-test finding from Step 7 is now in the cairn**. If they want to clean it up, the server admin can remove the file directly; there's no client-side delete.

Then stop. The user will direct what comes next.

## What you should *not* do

- Do not run `cairn init` or `cairn register --init` — the cairn exists remotely; creating a new local cairn here would conflict.
- Do not run `cairn collaborator add` — adding collaborators is a server-side operation. If the user isn't already a collaborator, stop and ask them to fix it server-side.
- Do not start a long-lived `cairn mcp` HTTP server. The user is a client, not a host.
- Do not write the bearer token into `cairn.toml`. Credentials live separately in `~/.config/cairn/credentials.toml`.
- Do not commit the credentials file. Confirm the user's `.gitignore` covers it if there's any chance the cairn config dir is inside a git repo.
- Do not invent a collaborator id, an endpoint URL, a cairn handle, or a token. If any is missing, stop and ask the user.

## If something fails

- **`cairn link` errors with "could not reach"**: surface the exact error; common causes are wrong endpoint, network issue, or server down.
- **HTTP 401/403** at any step: token wrong or expired. Re-collect from the user, redo Step 5.
- **First write returns `unknown author`**: the team hasn't added the user yet. Stop, ask them to fix server-side, retry.
- **`claude mcp add` doesn't accept `--transport http`**: the user's Claude Code may be older; check `claude mcp add --help` for their version's HTTP option, or edit `~/.claude.json` directly.
- **Any other error**: stop, show the user the exact text, ask how to proceed. Do not edit cairn state or config files by hand to "fix" things.

## Upgrading cairn later

To pick up the latest CLI:

```sh
pipx install --force 'cairn[mcp] @ git+https://github.com/cranmer/cairn'
```

Bundled skills live in the cairn on the server, not on the user's machine — they get updated by whoever runs the server, not here. `cairn skills sync` is a server-side operation; the user does not run it.

That's it. The user can now describe what they want to do next, and you should listen and capture transparently as the work happens — same posture as a standalone cairn.
