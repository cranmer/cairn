# Synthesis — multi-user / multi-cairn UX test run

**Run:** `20260523T175633Z`
**Branch:** `claude/multi-user-multi-cairn-test-run`
**Plan:** `tests/agent_smoke/multi-user-multi-cairn/` (merged via PR #26)

## Status

**Findings F-01, F-02, F-03, F-04, F-06, F-07, F-08, and F-10 are fixed
in this same PR** (#27). F-05 (`cairn whoami` at the CLI) and F-09
(`--branch` → `--exploration` rename, already noted in CLAUDE.md's
backlog) remain for follow-up. Full suite passes (269 tests; +14 new
tests for the fixes).

Scenario 2 — which was blocked at the start of this run by F-01 and
F-02 — is now executable against this branch and should be re-run as
a follow-up.

## Headline

The methodology surfaced **two critical bugs that block scenario 2
entirely**, and **one high-severity UX bug** independently surfaced by
both scenario-1 sub-agents as their single biggest mental-model
break. The scenario-2 blockers mean PR #25's HTTP transport surface is
not functional with the current `mcp>=1.27` library version. Scenario 1
ran to completion under an adapted methodology (CLI in place of MCP
tools — see "Adaptation" below) and produced six additional smaller
findings worth follow-up.

## Adaptation from the plan

The plan specified that sub-agents would call cairn MCP tools (whoami,
add_finding, etc.) over the configured transport. The parent Claude
session executing this run has no cairn MCP server registered, so
sub-agents inherit no `mcp__cairn__*` tools and cannot drive that
surface directly. Sub-agents instead exercised the **CLI** routing
surface (cairn.toml resolution, registry lookup, per-cwd write
dispatch), which is the same machinery the MCP server delegates to
server-side but tested via a different client.

What this preserves: cairn.toml pairing (US-P-12), registry routing
(ADR-0010), per-cairn state isolation, attribution end-to-end.

What this loses: the MCP-tool `cairn=<name>` parameter as the
disambiguation mechanism; `whoami` / `status` over the MCP wire; the
Tier-1 tool-call JSON-RPC layer; observed behavior under a real
MCP-tool consumer.

Recommended re-run: once the cairn MCP server can be registered against
the orchestrator's Claude session (or once the bundled-server-launcher
issue from finding #1 is fixed and the orchestrator can stand up a
local server pre-test), repeat scenario 1 driving sub-agents through
MCP tools. The CLI run here is a meaningful partial test, not a
replacement.

## Findings

### F-01 (CRITICAL — blocks scenario 2) — HTTP transport doesn't start

**Surface:** `cairn mcp --transport streamable-http --host 127.0.0.1 --port <N>`
**Reproduces:** every time, on first connection attempt.
**Failure:** `TypeError: FastMCP.run() got an unexpected keyword argument 'host'`

`src/cairn/cli/mcp_cmd.py:122` passes `host=`, `port=`, `path=` as
kwargs to `server.run(transport="streamable-http", ...)`. The installed
FastMCP (`mcp==1.27.1`) accepts host/port/path either via the
`FastMCP(...)` constructor or as `server.settings.host` / `.port` /
`.streamable_http_path`. The `run()` signature is only
`run(transport=..., mount_path=...)` — no host/port at all.

**Reproduction:**
```bash
cairn mcp --transport streamable-http --host 127.0.0.1 --port 8765
```

**Fix sketch** (one-line, mcp_cmd.py around line 119–124):
```python
if transport == "stdio":
    server.run()
else:
    server.settings.host = host
    server.settings.port = port
    if transport == "streamable-http":
        server.settings.streamable_http_path = path
        server.run(transport="streamable-http")
    else:
        server.settings.sse_path = path
        server.run(transport="sse")
```
A `cairn mcp --transport streamable-http` smoke test in CI would have
caught this. PR #25's tests cover the `mcp_cmd` CLI's option parsing
(`test_us_p_11_valid_transport_values_dont_fail_early`) but not actual
server startup against an installed `mcp` library.

**Verified workaround used for this run:** a `start-server.py`
launcher in `$TMPROOT` that imports `build_server()`, sets the three
settings directly, and calls `run(transport="streamable-http")`. With
this workaround the server starts and `uvicorn` reports
`Application startup complete` — but then finding F-02 trips immediately.

### F-02 (CRITICAL — blocks scenario 2) — Remote-MCP CLI client doesn't initialize an MCP session

**Surface:** `cairn finding add` (and presumably any other write) in a
project repo paired in remote-MCP mode.
**Reproduces:** first call, every time.
**Failure:**
```
error: HTTP 400 from http://127.0.0.1:<port>/mcp: {"jsonrpc":"2.0","id":"server-error",
"error":{"code":-32600,"message":"Bad Request: Missing session ID"}}
```

`src/cairn/mcp/remote.py:call_tool` POSTs a `tools/call` JSON-RPC
request directly with `Content-Type: application/json` and an optional
Bearer token. The streamable-HTTP MCP transport requires a session
lifecycle:

1. `POST initialize` → server returns response + sets
   `Mcp-Session-Id: <id>` response header.
2. `POST notifications/initialized` (with that header).
3. `POST tools/call` (with that header).

Without step 1, the server rejects every request with HTTP 400 / JSON
error code `-32600`. The current client implementation skips all of
this.

**Why this wasn't caught:** the existing test
(`tests/test_us_p_11_12_13_http.py`) covers the **CLI-side path** but
not the **server-side handshake** — it tests `call_tool` against a
mock or short-circuited server, not a real `cairn mcp` HTTP process.
A round-trip test (start server, write via CLI, read state file) would
have surfaced this immediately.

**Fix sketch:** implement the streamable-HTTP session-init handshake
before `tools/call`. The MCP Python SDK has a `streamable_http_client`
helper (`mcp.client.streamable_http`) that handles this; using it
removes the need to hand-roll session management in `remote.py`.

**Combined with F-01, scenario 2 cannot be executed against the
shipped PR #25 code.** The methodology has done its job (surfacing the
breakage); scenario 2 should be re-run after F-01 and F-02 land.

### F-03 (HIGH — UX) — Routing asymmetry: half the CLI honors `cairn.toml`, half doesn't

**Independently surfaced by both scenario-1 sub-agents** as their
single biggest finding. The same cwd, the same shell, opposite
behavior:

```
$ cd /tmp/cairn-run-.../projects/coral-bleach && cat cairn.toml
[cairn]
name = "coral-bleach"
$ cairn status
error: no cairn found at or above /tmp/cairn-run-.../projects/coral-bleach
$ cairn finding add --author kyle --title "..." --body "..."
Logged finding at knowledge/findings/2026-05-23-....md.
```

**Root cause** (one grep through `src/cairn/cli/`):

| Command | Resolver | Honors `cairn.toml`? |
|---|---|---|
| `decision add` | `resolve_target()` | yes |
| `finding add` | `resolve_target()` | yes |
| `action add/complete` | `resolve_target()` | yes |
| `status` | `resolve_or_exit()` | **no** |
| `orient` | `resolve_or_exit()` | **no** |
| `validate` | `resolve_or_exit()` | **no** |
| `exploration start/close` | `resolve_or_exit()` | **no** |
| `skills sync/...` | `resolve_or_exit()` | **no** |
| `collaborator add` | `resolve_or_exit()` | **no** |
| `link` | `resolve_or_exit()` | (correct — link is itself for *creating* pointers) |

The PR #25 upgrade to `resolve_target()` was applied to the three
write commands directly tied to remote-MCP dispatch but not to the
read / utility commands. The mental model break is sharp: users learn
"I can write from my project repo" but then trip immediately on
"I can't `cairn status` from my project repo." Both sub-agents reached
for `cairn status` early to sanity-check pairing, and both got the
"no cairn found" error from a *correctly-paired* project repo.

This is also compounded by F-04 below — the error message gives no
hint that the pointer was even seen.

**Fix sketch:** swap `resolve_or_exit()` for `resolve_target()` in the
six commands above. For remote-MCP targets, status/orient need a
fallback (the cairn is remote; status would need to call the MCP
server). For local-registry and local-path pointers (which is what
sub-agents tested), the swap is direct. Even shipping just
local-mode-aware resolution would unblock the most common single-user
scenario.

### F-04 (MEDIUM — UX) — "No cairn found" error masks F-03

The error wording is identical in two completely different cases:

1. **Genuine miss:** `cd /tmp && cairn finding add ...` → "no cairn found at or above /tmp" (correct)
2. **False negative inside a paired repo:** `cd /tmp/.../projects/lit-monitor && cairn status` → "no cairn found at or above /tmp/.../projects/lit-monitor" (wrong — the pointer was ignored, not absent)

The message doesn't mention `cairn.toml` at all. A user staring at this
in a directory whose pointer they just wrote with `cairn link` would
reasonably conclude pairing is broken. Both sub-agents flagged the
identical wording as masking the underlying bug.

**Fix sketch (independent of F-03):** when no cairn marker is found at
or above cwd, but a `cairn.toml` *is* present, surface that in the
error:
```
error: no cairn found at or above <cwd>
  (note: cairn.toml pointer at <path> is not honored by this command yet)
```
This is a band-aid that's still better than the current silence.

### F-05 (MEDIUM — gap) — No `cairn whoami` at the CLI

The MCP server exposes a `whoami` tool but the CLI surface doesn't.
Sub-agent A noted: with `state/collaborators.yaml` listing multiple
collaborators, there's no way to ask "what identity will my next write
use?" before running a write. Combined with F-03 (`cairn status` doesn't
resolve cairn.toml), there's no easy way to probe "which cairn am I in
right now?" either.

**Recommendation:** add `cairn whereami` or `cairn whoami` at the CLI
that mirrors the MCP tool. Output should include: resolved cairn name +
path, the cairn-pointer chain that resolved it, and the cwd's git
identity matched against `state/collaborators.yaml`.

### F-06 (LOW — cosmetic) — Finding slug truncates mid-word, leaving dangling hyphens

Two real examples from this run:

- `2026-05-23-methods-comparison-paper-arxiv-2403-04567-is-worth-a-closer-.md` (note trailing `-`)
- `2026-05-23-transect-methodology-paper-arxiv-2403-04567-relevant-to-base.md` (truncated at "base")

The slug heuristic in `finding_cmd._kebab` slugifies then truncates to
60 chars without stripping trailing dashes or rewinding to a
word-boundary.

**Fix sketch:** `slug = slug[:60].rstrip("-")` after truncation. (One
line.)

### F-07 (LOW — convention) — `cairn --version` doesn't work (only `cairn version`)

Both sub-agents tried `cairn --version` first by habit. The CLI only
accepts the subcommand form. Adding a Typer `--version` callback at the
root would be one line.

### F-08 (LOW — UX) — `cairn decision add` output is terser than `cairn finding add`

Both sub-agents flagged this asymmetry:

- `cairn finding add` → `Logged finding at knowledge/findings/<path>.md.`
- `cairn decision add` → `Recorded D-002.`

Decisions give the id but no path. Findings give the path but no id
(there is no F-NNN concept). A unified `Recorded D-002 at state/decisions.yaml (related: Q-001).` line
on decisions would close the loop — particularly the `related` echo,
since right now there's no acknowledgement that the cross-reference
was accepted.

### F-09 (LOW — known) — `cairn status --json` `branch` field returns `"current"`, not exploration name

JSON output shape:
```json
{ "branch": "current", "git_branch": "master", ... }
```

The literal `"current"` is the un-renamed user-facing label leaking
into JSON output. Already noted in CLAUDE.md's backlog ("Rename
`cairn status --branch` flag to `--exploration` per ADR-0008"); this
run confirms it survives into JSON-mode output too.

### F-10 (LOW — stale help) — `cairn collaborator add --type` help text omits `group` and `unknown`

The schema (`schemas/collaborators.py`) accepts
`Literal["human", "ai-collaborator", "group", "unknown"]` (per
ADR-0011). The CLI option help says only `'human' or 'ai-collaborator'`.
The CLI *accepts* `--type unknown` (the orchestrator used it to register
the `repo-history` collaborator), but help-text discoverability is
broken.

## Scenario 1 scoring (against acceptance criteria A1–A6 from the scenario doc)

Adapted to the CLI surface this run actually tested.

| Criterion | Original framing | Result | Notes |
|---|---|---|---|
| A1 | Default routing in paired-cwd writes to the right cairn | **PASS for writes**, **FAIL for status** | Headline finding F-03. Writes route correctly via cairn.toml; reads don't see the pointer at all. |
| A2 | Explicit cairn-name addressing routes correctly | **N/A — adapted** | CLI has no `--cairn` flag. Tested instead by cwd-switching; routing was clean (writes from each project repo landed in the right cairn). |
| A3 | Error on unknown cairn names the registered cairns | **N/A — adapted** | Same: no CLI cairn-name parameter to probe. Closest analog is the `no cairn found` error from an unpaired cwd, which is terse — see F-04. |
| A4 | `whoami` returns per-cairn collaborator lists | **N/A — gap** | No `cairn whoami` at the CLI. See F-05. |
| A5 | `status` returns per-cairn state, not a merged view | **PASS** | Once status was reachable (from cairn root), each cairn's counts were isolated and correct. |
| A6 | Agent posture stays consistent — no "which user am I" confusion | **PASS** | Both sub-agents reported zero identity uncertainty across the run. |

**Bonus criterion (would-fail observation): no silent mis-routing.** Sub-agent B
flagged a lit-monitor finding it didn't write ("Methods-comparison
paper (arxiv 2403.04567)..."). Orchestrator verified by reading state:
the finding was correctly written by sub-agent A's task 5 cross-cairn
write, attributed to `kyle`, and landed in the lit-monitor cairn —
exactly where it was supposed to go. Sub-agent B's instinct to flag an
unfamiliar-looking entry was correct test discipline (the methodology
asks for surprises to be surfaced), and the system did the right thing.

## Scenario 2 scoring

**BLOCKED.** Cannot execute as designed against shipped PR #25 code.
F-01 (HTTP server won't start) and F-02 (CLI doesn't do MCP session
init) need to land first. Once they do, scenario 2 should run as a
follow-up and the run + this synthesis should be amended.

Setup that was completed (and still on disk in `$TMPROOT/cairns/shared-physics-paper`):

- Cairn scaffolded with 4 collaborators (alex / morgan / sam / repo-history).
- 1 baseline decision (D-001 by alex), 1 open question (Q-001 by morgan), 1 baseline finding (alex).
- Project repo at `$TMPROOT/projects/shared-physics-paper` paired
  via `endpoint + name` cairn.toml at the chosen port.

Three sub-agent backlogs were drafted but not handed off, since the
transport blocked. They'll be reusable on re-run.

## Recommendations (ranked)

1. **Fix F-01 + F-02 (HTTP transport end-to-end).** Without these, PR #25's HTTP-transport surface is broken end-to-end. One small fix in `mcp_cmd.py` for F-01; a more substantial refactor in `mcp/remote.py` for F-02 (probably worth adopting the MCP SDK's `streamable_http_client` helper instead of hand-rolling the protocol). Add a server-round-trip test to prevent regression.
2. **Fix F-03 (routing asymmetry).** Swap `resolve_or_exit()` for `resolve_target()` across the six read/utility commands listed in F-03's table. For remote-MCP targets, status/orient need a server-call fallback; for local modes, the swap is direct. This is the single biggest UX win for the user mental model.
3. **Add F-05 (`cairn whoami` / `whereami`).** Closes the "which cairn / which identity am I about to use?" probe gap. Particularly valuable in multi-cairn workflows.
4. **Cosmetic batch — F-04, F-06, F-07, F-08, F-09, F-10.** Six low-cost touch-ups, all roughly one-line fixes or stale-help-text updates. Could land as a single small PR.

## Methodology notes

What worked:

- **Independent feedback files surfaced the same headline finding (F-03) from both sub-agents.** That cross-confirmation is what made it the clear top recommendation rather than a one-off.
- **Sub-agent B's "surprise: a finding I didn't write" flag.** The methodology explicitly asks for surprises in section 10; B did exactly the right thing, and the orchestrator could verify (correct cross-cairn write from A, not mis-routing) using the state files. This is the kind of cross-agent observability the plan was designed for.
- **The "no MCP server in parent env" adaptation.** It surfaced six real findings via CLI alone. The MCP-specific surface still needs a real re-run, but the CLI run was far from wasted.

What didn't work:

- **Scenario 2 BLOCKED before launch.** Two transport-layer bugs prevented even smoke-testing the multi-user surface. This is itself a finding *for* the methodology — but it also means scenario 2's three sub-agents got drafted backlogs and no actual run.
- **The plan assumed Claude-Code-on-the-web sessions could register their own MCP servers per-sub-agent.** They can't; sub-agents inherit the parent's MCP config. The plan's `XDG_CONFIG_HOME` isolation tactic only isolates the cairn-side registry, not the MCP-server registration. A future revision should call this out and document the CLI-fallback explicitly, instead of leaving it as an in-flight adaptation.

## Artifacts

- `runs/20260523T175633Z/scenario-1-kyle-coral-bleach.md` — sub-agent A feedback (full)
- `runs/20260523T175633Z/scenario-1-kyle-lit-monitor.md` — sub-agent B feedback (full)
- `runs/20260523T175633Z/SYNTHESIS.md` — this file

The `/tmp/cairn-run-20260523T175633Z/` tmpdir holds the scaffolded
cairns + project repos + the HTTP server log + the workaround launcher
used to exercise F-01 and F-02. It will be garbage-collected when this
container is reclaimed — nothing in it needs to be preserved beyond
what's in this synthesis.
