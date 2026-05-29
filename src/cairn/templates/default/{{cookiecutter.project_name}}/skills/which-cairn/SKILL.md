---
name: which-cairn
description: Use when the user asks "which cairn am I using?", "what server is this?", "am I on local or remote?", "how do I switch cairns?", or similar questions about the current cairn MCP connection. Calls `whoami` to read transport, endpoint, and the list of registered cairns; explains how to switch.
---

# Which cairn server is this?

When the user asks any of:

- "Which cairn am I using?" / "What cairn is this?"
- "Which server am I connected to?" / "Is this local or remote?"
- "What's the endpoint?" / "What URL am I pointing at?"
- "How do I switch to a different cairn server?"
- "Why don't I see my decisions from the other project here?"

…this is the skill.

## What to do

1. **Call `whoami`** (no `cairn` parameter needed if there's only one registered). The response includes a `server` block:

   ```json
   {
     "server": {
       "transport": "stdio" | "streamable-http" | "sse",
       "endpoint": "http://127.0.0.1:8765/mcp" | null,
       "registered_cairns": ["coral-bleach", "lit-monitor"]
     },
     "cairn": "coral-bleach",
     "cairn_path": "/home/kyle/cairns/coral-bleach",
     ...
   }
   ```

   - `transport: "stdio"` + `endpoint: null` → the server is running locally as a subprocess of Claude Code; the cairns it serves are on this machine's disk.
   - `transport: "streamable-http"` (or `"sse"`) + an `endpoint` URL → the server is a long-lived HTTP service somewhere; cairns live on that host's disk, not the user's.

2. **Summarize plainly for the user.** Three pieces of information:

   - Which cairn the current write would go to (`cairn` field).
   - Whether the server is local or remote (`transport` and `endpoint`).
   - Which other cairns this server knows about (`registered_cairns`).

   Sample reply:

   > *"You're currently writing to **coral-bleach** (local stdio server; cairn directory `/home/kyle/cairns/coral-bleach`). This server also knows about **lit-monitor** — pass `cairn=\"lit-monitor\"` on any tool call to write there instead."*

   For a remote-HTTP setup:

   > *"You're connected to the group's HTTP cairn server at `https://cairn.lab.example.org/mcp`, currently writing to **shared-physics-paper**. The server has just this one cairn registered."*

## When the user asks how to switch

The answer depends on what kind of switch they mean:

### "Write to a different cairn the *same* server knows about"

No switch needed. The MCP tool's `cairn` parameter selects which one. Pass `cairn="<name>"` on the next write:

```
add_finding(cairn="lit-monitor", author="kyle", title="...", body="...")
```

The names in `whoami`'s `server.registered_cairns` are valid values.

### "Switch which server Claude Code talks to"

That's a Claude Code config change, not something the MCP server can do for itself. Tell the user:

> *"Claude Code's MCP-server set is controlled by `claude mcp` commands. Run `claude mcp list` to see what's registered; `claude mcp remove <name>` to drop one; `claude mcp add ...` to add another. After changes, restart any open Claude Code sessions to pick up the new set."*

If the user wants both local and remote available at the same time, both can be registered (typically under different names like `cairn` and `cairn-remote`); the agent then has access to `mcp__cairn__*` AND `mcp__cairn-remote__*` tools and the user picks which one in conversation.

### "Pair my project repo with a different cairn"

This is a `cairn.toml` change. Direct the user at:

```sh
# In their project repo:
cairn link --name <other-cairn>                    # different local cairn
cairn link --endpoint <url> --name <handle>        # switch to a remote one
cairn link --force ...                             # overwrite an existing pairing
```

After re-linking, agents working in that project repo route to the newly-paired cairn automatically.

## Do not

- Do not edit the user's `~/.claude.json`, `~/.config/cairn/server.toml`, or `cairn.toml` files on their behalf to "switch" things. These are config files the user owns — surface the commands and let them run.
- Do not invent server endpoints or cairn names. If `whoami` returns a list, the names in it are the only ones this server knows about.
- Do not assume cwd determines the cairn at the MCP layer — it determines the cairn at the CLI layer. For MCP tools, the `cairn` parameter is what discriminates.

## Acceptance criteria

- The user gets a one-paragraph answer to "which cairn am I using?" that names the cairn, the server, and the alternatives.
- If they ask "how do I switch?", they get the command shape relevant to the *kind* of switch they mean (cairn vs server vs project pairing).
- No silent edits to user-owned config files.
