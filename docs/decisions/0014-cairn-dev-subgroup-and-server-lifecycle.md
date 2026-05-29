# 0014 — `cairn dev` CLI subgroup, detached server lifecycle, in-package fixture catalog

## Context

The multi-user/multi-cairn test methodology (`tests/agent_smoke/multi-user-multi-cairn/`) needs a reproducible setup: spin up an HTTP MCP server, scaffold one or more fixture project/cairn pairs, point sub-agents at them, tear everything down. Doing that by hand — or worse, having each sub-agent reinvent the steps inside a test transcript — wastes context and produces flaky runs whose failures don't reproduce on a second attempt.

US-T-01 motivated a small CLI surface for this. Three design choices had to be made before the first command landed:

1. **Where the dev surface lives in the CLI.** Mixed into the operator-facing root (`cairn serve-dev`, `cairn scaffold-fixture`, …) or partitioned into a separate namespace.
2. **How the dev server outlives the spawning terminal.** A foreground process tied to the test script's tty (cleanest semantics, useless for an agent that needs to disconnect) versus a detached background process with a state file (more lifecycle plumbing, but matches what `cairn dev list` / `--all` actually need).
3. **How fixtures are defined.** On-disk YAML or directory templates the operator could in principle edit, versus Python constants compiled into the package.

[ADR-0013](0013-server-side-fixture-scaffold-tool.md) later added a server-side `scaffold_fixture` MCP tool on top of this foundation. The choices below are what 0013 builds on; they should have been documented at the time and are recorded here retrospectively.

## Decision

### A `cairn dev` Typer subgroup, walled off from operator commands

All test-harness CLI lives under `cairn dev *`:

- `cairn dev serve` / `stop` / `list`
- `cairn dev scaffold-fixture`
- `cairn dev fixtures`

The subgroup's help text explicitly names its non-production role: "Development & test-harness helpers — not for production cairn use." This buys three things:

- **Discoverability without contamination.** A new operator running `cairn --help` sees a single `dev` line and can ignore it; they never see eight test-only commands cluttering the top-level surface.
- **Room to grow.** New test-harness commands (future `cairn dev reset`, `cairn dev seed`, …) don't have to fight for namespace with operator concepts.
- **A clean gate point.** Anything under `cairn dev` is fair game to require a co-installed dev extra or to refuse to run against a registered production cairn, if that ever becomes necessary. The boundary is a single Typer app, not a per-command convention.

The corresponding server-side gate is `cairn mcp --allow-dev-tools`, which `cairn dev serve` always passes ([ADR-0013](0013-server-side-fixture-scaffold-tool.md) "Gating"). The CLI and MCP boundaries are deliberately the same shape.

### Detached HTTP server with `start_new_session=True` and an XDG-cache state file

`cairn dev serve` spawns `cairn mcp --transport streamable-http …` as a child process with `start_new_session=True`, severing the controlling-terminal relationship. The parent CLI returns immediately after the server reports `listening on …` in its log, printing `pid`, `port`, `url`, and `log` to stdout.

A state file at `$XDG_CACHE_HOME/cairn/dev-servers/state.toml` (typically `~/.cache/cairn/dev-servers/state.toml`) records one entry per running dev server:

```toml
[[server]]
pid = 12345
port = 51234
url = "http://127.0.0.1:51234/mcp"
cairn_path = "/abs/path/to/cairn"   # optional
log_path = "~/.cache/cairn/dev-servers/12345/server.log"
started_at = "2026-05-23T19:24:55Z"
```

This is the substrate `cairn dev list` reads from, `cairn dev stop --pid N` updates, and `cairn dev stop --all` iterates over. It is not a registry of cairns — that lives elsewhere (`~/.config/cairn/server.toml` for production per [ADR-0010](0010-single-mcp-server-multiple-cairns.md); the per-pid dev sandbox registry per [ADR-0013](0013-server-side-fixture-scaffold-tool.md)).

Three operational properties fall out:

- **Free-port allocation.** `--port` defaults to bind-port-0; the actual port is read back from the server's startup log and written to the state file. Two test scripts in the same shell can each call `cairn dev serve` without coordinating.
- **Stale entry pruning.** Before every `list` / `stop`, entries whose pid is no longer alive are dropped from the state file. A `kill -9`'d server doesn't leave permanent garbage; the next `list` cleans up.
- **Per-pid sandbox.** Each dev server gets `$XDG_CACHE_HOME/cairn/dev-servers/<pid>/` for its log file, its registry (in dev-tools mode), and any server-side scaffolded cairns. `cairn dev stop` removes the whole sandbox dir.

Why XDG-cache rather than XDG-runtime or `/tmp`: tests routinely outlive a single login session (a CI job, a long methodology run); XDG-runtime is wiped on logout. `/tmp` is wiped on reboot and has no per-user partitioning convention. XDG-cache survives both and is the convention for "ephemeral but not session-scoped."

### Fixtures live in the `cairn` package as Python constants

`cairn.dev.fixtures_data.FIXTURES` is a `dict[str, Fixture]` where `Fixture` is a frozen dataclass carrying:

- A list of collaborators (id, name, role, agent flag).
- Decisions, open questions, action items, findings — each a dataclass instance with the same shape as the corresponding state-file schema.
- A list of fictional project-repo files (relative path + content) and the git commit sequence that builds them.

The three fixtures today are `coral-bleach`, `lit-monitor`, and `shared-physics-paper`. The names and what makes each distinct are mirrored in `tests/agent_smoke/multi-user-multi-cairn/fixtures/README.md` so a human reader of the test methodology doesn't have to read Python to know what the fixtures represent.

Why in-package constants rather than on-disk YAML or directory templates:

- **Fixtures travel with the package version.** The drift-detection contract in [ADR-0013](0013-server-side-fixture-scaffold-tool.md) — "if the server and client cairn versions disagree on a fixture's contents, abort with a clear error" — only works if the fixture *definition* is the same shape as the package version. Code-shaped fixtures get that for free.
- **No new file format to design.** YAML fixtures would need their own schema, their own validator, and a place in the repo layout. They would also be a new attack surface — anything the test harness reads off disk is a candidate for "but what if the user edits it." Python constants are trusted-by-construction.
- **The substrate-as-specification commitment is unaffected.** Fixtures are *test scaffolding*, not part of any cairn's on-disk state. A real cairn never reads `FIXTURES`. The principle applies to cairns, not to the framework's test code.

The cost is that an operator who wants a custom fixture must vendor or fork the package. This is the right tradeoff for a closed set of test fixtures and is explicitly the "trigger for revisiting" criterion in ADR-0013: when user-defined fixtures become a requirement, both this ADR and 0013 need to extend.

## Consequences

- **The test methodology has a one-line setup.** `cairn dev serve` + one or more `cairn dev scaffold-fixture` calls is enough to put a sub-agent in front of a deterministic project/cairn pairing. The methodology recipe at `tests/agent_smoke/multi-user-multi-cairn/` uses these commands directly rather than re-deriving setup.

- **Production CLI is unchanged.** Nothing outside `cairn dev *` learned a new flag, gained a new code path, or shifted in default behavior. The operator-facing surface stays committed to operator workflows.

- **The state file is the contract.** Test scripts (and `cairn dev list --json`, when it ships) read `$XDG_CACHE_HOME/cairn/dev-servers/state.toml` to discover running servers. The schema there is small and stable; future fields are additive.

- **`cairn dev serve` always implies the dev-tools gate.** Because dev mode and the dev-only MCP tools share the same trust boundary, the gate is on the CLI command, not a separate flag the caller can forget. This is why [ADR-0013](0013-server-side-fixture-scaffold-tool.md) could commit to "the flag is one gate for the whole *category* dev tools" — the command above the SDK call is the gate.

- **Fixtures evolve in code review.** Changes to `FIXTURES` show up as diffs in `cairn/dev/fixtures_data.py`, go through the same review path as schema or CLI changes, and ride along with the package version. There is no "fixture data update" out-of-band channel.

- **Trigger for revisiting:** if non-test consumers ever depend on a `cairn dev *` command (e.g., a future Phase-5 agent uses `cairn dev serve` to host its own MCP), the wall between dev and operator surfaces collapses and a real ADR has to decide which surface that command belongs to. Until that pressure exists, the wall stays.

## Alternatives considered

- **Mixed CLI surface** (`cairn serve-dev`, `cairn scaffold-fixture` at the top level). Smaller, but pollutes `cairn --help` and offers no gate point for future "this is dev-only" enforcement. Rejected.

- **Foreground server with the caller responsible for backgrounding.** Cleaner semantically (no PID state file, no detach), but unusable in practice: an agent invoking `cairn dev serve` from inside a Bash tool can't keep the process alive after the tool returns without inventing its own daemonization. Rejected.

- **On-disk YAML fixtures with a loader.** Editable, more "data-driven," but introduces a schema, a validator, and a directory layout to maintain. The drift-detection requirement from [ADR-0013](0013-server-side-fixture-scaffold-tool.md) would need to compare loaded YAML structures across versions — strictly harder than comparing dataclass attributes. Rejected; revisit only if user-defined fixtures become a requirement.

- **`/tmp` for dev-server state.** Loses across reboots, has no per-user partitioning, and is shared with every other process on the box. XDG-cache is the established convention for the "ephemeral but not session-scoped" tier. Rejected.

- **A `/var/run`-style PID directory.** Cleaner in shape but requires root or sudo to write. Dev servers must run as the invoking user. Rejected.
