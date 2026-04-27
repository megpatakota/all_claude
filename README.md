# mcp-future-demo

End-to-end FastMCP demo, inspired by **"The Future of MCP"** (David Soria Parra,
Anthropic — https://www.youtube.com/watch?v=v3Fr2JR47KA).

This first slice covers the three **core MCP primitives** the talk grounds
everything else in:

| Primitive   | What it is                                | Demonstrated by              |
|-------------|-------------------------------------------|------------------------------|
| **Tools**     | Callable functions the agent can invoke | `add_note`, `search_notes`, `delete_note` |
| **Resources** | Data the agent can read by URI          | `notes://list`, `notes://{id}` |
| **Prompts**   | Reusable prompt templates               | `summarize_notes`, `daily_review` |

Newer primitives from the talk (tasks, sampling, elicitation, OAuth, remote
HTTP streaming, MCP Apps, registry) are tracked in [`backlog.md`](./backlog.md).

**New here?** Read [`docs/EXPLAINER.md`](./docs/EXPLAINER.md) — a walkthrough
of MCP from first principles, mapped onto the code in this repo.

## Layout

```
server/notes_server.py   # FastMCP server (stdio)
client/journey.py        # MCP client that exercises every primitive
pyproject.toml           # mcp dependency
backlog.md               # deferred MCP aspects from the talk
```

## Run the journey

Install with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run python client/journey.py
```

The client spawns the server over stdio, then walks through `initialize` →
`tools/list` → `tools/call` → `resources/list` → `resources/read` →
`prompts/list` → `prompts/get`, printing each step.

## API key

`agent.py` loads `ANTHROPIC_API_KEY` from `.env` via `python-dotenv`. Create
the file at the repo root:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

`.env` is protected by four layers: `.gitignore` (line 141), `python-dotenv`
isolation (only `agent.py` reads it), Claude Code's sandbox denylist
(`./.env` is unreadable), and an explicit `Read(./.env)` deny rule in
[`.claude/settings.json`](./.claude/settings.json).

## Chat UI (web)

A small FastAPI + HTML chat page wraps the agent loop. Type a message,
watch the model call MCP tools inline.

```bash
uv sync
./scripts/web.sh
open http://localhost:8000
```

Lives in `web/` — `app.py` (~80 lines) streams events as SSE,
`index.html` (~190 lines) is a hand-written chat page (no Streamlit, no
framework).

## Chat UI (Claude Desktop)

Anthropic's official chat app. Free, polished, MCP-native.

1. Install: https://claude.ai/download
2. Add this server to its config at
   `~/Library/Application Support/Claude/claude_desktop_config.json`:

   ```json
   {
     "mcpServers": {
       "notes-kb": {
         "command": "/Users/megpatakota/git_projects/all_claude/.venv/bin/python",
         "args": ["/Users/megpatakota/git_projects/all_claude/server/notes_server.py"]
       }
     }
   }
   ```
3. Restart Claude Desktop. The notes-kb tools appear under the 🔌 icon —
   ask *"what notes do I have?"* to verify.

## See it used by a real model (`agent.py`)

The full loop — model picks tools, MCP runs them, model writes the answer:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
uv run python agent.py
# or with your own task:
uv run python agent.py "find notes about transports and add a TL;DR note"
```

The script connects Claude (Anthropic API) to the notes server (MCP) via the
SDK's `async_mcp_tool` adapter, then prints every step so you can watch the
loop. Uses `claude-opus-4-7` with adaptive thinking.

## Use from Claude Code (project-scoped)

A `.mcp.json` at the repo root registers `notes-kb` for this project. Restart
Claude Code in this directory and ask things like *"search my notes for MCP"*
— Claude Code will call the tool itself.

## Explore in a UI (MCP Inspector)

Anthropic ships an official browser UI for exploring MCP servers — the
[MCP Inspector](https://github.com/modelcontextprotocol/inspector). Use it to
poke tools, read resources, and watch the JSON-RPC traffic live.

```bash
./scripts/inspect.sh
```

(Requires Node.js — Inspector runs via `npx`. First launch downloads it.)

The script wires Inspector up to spawn our notes server over stdio. Open the
URL it prints, then click around the **Tools / Resources / Prompts** tabs.

## Use the server from Claude Desktop / Claude Code

Add to your MCP client config:

```json
{
  "mcpServers": {
    "notes-kb": {
      "command": "uv",
      "args": ["--directory", "/Users/megpatakota/git_projects/all_claude",
               "run", "python", "server/notes_server.py"]
    }
  }
}
```
