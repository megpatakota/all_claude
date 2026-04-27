# Understanding MCP — a walkthrough of this project

A plain-English tour of the Model Context Protocol, mapped onto the code in
this repo. Read top-to-bottom; every concept is grounded in a file you can
open.

---

## 1. The one-sentence definition

> MCP is a JSON-RPC protocol that lets an **AI app (host)** plug into
> external **servers** that expose data and capabilities, without the app
> needing custom code per integration.

Think USB-C, but for connecting LLMs to the outside world. Before MCP, every
AI app had to hand-roll integrations for Slack, GitHub, your filesystem, etc.
With MCP, anyone writes one server and every MCP-aware client can use it.

## 2. The three actors

```
┌──────────┐     JSON-RPC     ┌──────────┐
│  Host    │ ───────────────► │  Server  │
│ (Claude  │ ◄─────────────── │ (yours)  │
│ Desktop, │                  │          │
│ Inspector)│                 └──────────┘
└──────────┘
     │
     │ embeds
     ▼
┌──────────┐
│  Client  │   one per server connection
└──────────┘
```

- **Host** — the user-facing AI app (Claude Desktop, Claude Code, the
  Inspector, your own agent).
- **Client** — a *connection object* inside the host, one per server. The
  host can hold many clients at once.
- **Server** — what you write. It exposes capabilities through MCP primitives.

In this repo:
- `server/notes_server.py` is the server.
- `client/journey.py` is a hand-rolled client that talks directly to the server.
- The MCP Inspector (launched via `scripts/inspect.sh`) plays the host role.

## 3. The transport — how bytes actually move

MCP is **transport-agnostic**. Two transports matter today:

| Transport | When to use | How it works |
|-----------|------------|--------------|
| **stdio** | Local servers running on the user's machine | Host spawns the server as a child process, reads/writes JSON-RPC over stdin/stdout |
| **HTTP streaming** | Remote / hosted servers | Server listens on HTTP; client opens a streaming connection (SSE-style) |

Our server uses **stdio** (the `mcp.run()` call at the bottom of
`notes_server.py`). When you run `client/journey.py`, this happens:

```
client process ──spawns──► server subprocess
       ▲                          │
       └─────── stdin/stdout ─────┘
```

Every message is one line of JSON. The protocol on top of those bytes is
standard **JSON-RPC 2.0** — request / response with `id`, `method`, `params`.

## 4. The lifecycle of a connection

Every MCP session goes through the same opening dance:

1. **`initialize`** — client says "hi, I support protocol version X, here are
   my capabilities." Server responds with its name, version, and what it can
   do (tools? resources? prompts?).
2. **`tools/list`, `resources/list`, `prompts/list`** — client discovers
   what's on offer.
3. **`tools/call`, `resources/read`, `prompts/get`** — actual work happens.
4. Connection stays open; either side may send notifications
   (e.g. "the resource list changed").

Look at `client/journey.py` — it walks each of those steps and prints what
comes back. This is the canonical MCP handshake.

## 5. The three core primitives

These are what your server exposes. Everything else in MCP builds on them.

### Tools — *the model decides when to call them*

A tool is a function. The host shows its name + description + input schema to
the LLM. The LLM decides "I should call `search_notes` with query='mcp'", and
the host invokes it on the user's behalf.

```python
@mcp.tool()
def search_notes(query: str) -> list[dict[str, Any]]:
    """Case-insensitive substring search across note title, body, and tags."""
    ...
```

FastMCP introspects the type hints and docstring to auto-build the JSON
schema — no manual schema writing. The docstring becomes the description the
model sees, so write it for the model, not for humans.

**Mental model**: tools are **model-controlled**. The model picks when and how.

### Resources — *the user (or app) decides what to load*

A resource is data addressable by URI. The user (or the app on their behalf)
attaches a resource to the conversation; the model then sees its contents.

```python
@mcp.resource("notes://list")
def list_notes() -> str: ...

@mcp.resource("notes://{note_id}")   # template — note_id is a path param
def get_note(note_id: str) -> str: ...
```

Two flavours:
- **Static resources** (`notes://list`) — fixed URI, always present.
- **Resource templates** (`notes://{note_id}`) — URI patterns the client can
  fill in. The client lists templates separately (`resources/templates/list`).

**Mental model**: resources are **app-controlled**. The model only sees what
the app chose to load.

> Tools vs resources is the most common point of confusion. The split is about
> *control*, not *data shape*. If the model should decide, make it a tool.
> If the user/app should decide, make it a resource. A "search" is a tool; a
> "file you've already opened" is a resource.

### Prompts — *the user picks them from a menu*

A prompt is a reusable template the user can invoke (often via slash command
or menu). It returns one or more messages that get prepended to the
conversation.

```python
@mcp.prompt()
def summarize_notes(topic: str) -> str:
    return f"Using the search_notes tool, find notes related to '{topic}'..."
```

**Mental model**: prompts are **user-controlled**. They surface in the host's
UI as something to click.

### Quick comparison

| Primitive | Who triggers it | Example in this repo |
|-----------|----------------|----------------------|
| Tool      | Model          | `search_notes`, `add_note`, `delete_note` |
| Resource  | App/user       | `notes://list`, `notes://{id}` |
| Prompt    | User           | `summarize_notes`, `daily_review` |

## 6. What FastMCP does for you

`FastMCP` (the `from mcp.server.fastmcp import FastMCP` import) is a thin
ergonomic layer on top of the raw MCP server SDK. It handles:

- **JSON-RPC plumbing** — you never write `{"jsonrpc": "2.0", "method": ...}`.
- **Schema generation** — type hints become JSON Schema for tools/prompts.
- **Decorator registration** — `@mcp.tool()`, `@mcp.resource(uri)`,
  `@mcp.prompt()` register handlers.
- **Transport choice** — `mcp.run()` defaults to stdio; pass
  `transport="streamable-http"` for HTTP.

Without FastMCP you'd write the request handlers, JSON Schema, and dispatch
logic by hand. The plain SDK is still there for cases where you need fine
control.

## 7. Reading the wire — what JSON-RPC actually flies past

When `journey.py` calls `session.call_tool("search_notes", {"query": "mcp"})`,
this goes over the wire:

```jsonc
// → client to server
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": { "name": "search_notes", "arguments": { "query": "mcp" } }
}

// ← server to client
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [{"type": "text", "text": "[{\"id\": 1, ...}]"}],
    "isError": false
  }
}
```

The Inspector shows this traffic in its session log — a great way to build
intuition about what's actually happening.

## 8. Where to go next

The video grouped MCP's future into three buckets. We've built the foundation;
each line in `backlog.md` is one next step:

- **Newer primitives** — tasks (async), sampling (server asks the client's
  model), elicitation (server asks the user), roots, completion.
- **Transport & auth** — HTTP streaming, OAuth 2.1, progress notifications.
- **Ecosystem** — MCP Apps (iframe UIs), registries, agent-to-agent.

Pick one and extend the notes server.

## 9. Glossary

- **JSON-RPC** — a tiny RPC format: `{method, params, id}` in,
  `{result, id}` or `{error, id}` back. MCP is JSON-RPC 2.0 over a transport.
- **stdio** — standard input / standard output. The simplest possible
  transport: pipe one process to another.
- **Capability** — a feature flag in the `initialize` exchange (e.g.
  "I support resources"). Lets host and server negotiate.
- **Host vs client** — the host is the app the user sees; clients are
  per-server connection objects living inside it.
- **Inspector** — Anthropic's official MCP debugging UI.
  `npx @modelcontextprotocol/inspector <command>`.
