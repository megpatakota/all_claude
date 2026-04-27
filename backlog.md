# Backlog — MCP aspects from "The Future of MCP"

Source: David Soria Parra, Anthropic — https://www.youtube.com/watch?v=v3Fr2JR47KA

The current repo covers the three **core primitives** (tools / resources / prompts).
Everything below is intentionally deferred — pick one when you want to extend the demo.

## Newer primitives

- [ ] **Tasks** — long-running, asynchronous agent operations. Container for async
      work rather than wrapping a synchronous tool. Enables deep research and
      agent-to-agent handoffs.
- [ ] **Sampling** — server asks the *client's* model to complete something
      (server-initiated LLM calls). Demo idea: a `summarize_note` tool that
      sampling-calls back into the host model.
- [ ] **Elicitation** — server asks the user for structured input mid-call.
      Demo idea: `add_note` elicits missing tags interactively.
- [ ] **Roots** — let the server know which filesystem/workspace roots the
      client trusts. Demo idea: scope notes to a specific roots-defined folder.
- [ ] **Completion** — argument autocompletion for tool/prompt parameters.

## Transport & auth

- [ ] **HTTP streaming transport** — run the same server remotely over
      streamable HTTP instead of stdio.
- [ ] **OAuth 2.1** — split resource server from identity provider, dynamic
      client registration. Required before this is enterprise-deployable.
- [ ] **Notifications / progress** — push `notifications/progress` from a
      long-running tool back to the client.

## Ecosystem

- [ ] **MCP Apps (iframe UI)** — return a UI surface (e.g. note picker) instead
      of plain text. The talk calls out shopping/seat-selection as the killer
      use case.
- [ ] **Registry** — publish this server to an MCP registry with signature
      verification ("npm for agents"). Try Smithery or the official registry.
- [ ] **Agent-to-agent** — second MCP server that calls the notes server as
      a downstream agent, demonstrating handoff.

## Hardening

- [ ] Replace in-memory `NOTES` dict with SQLite so state survives restarts.
- [ ] Add tests (pytest + `mcp` test client).
- [ ] Type-check with `mypy --strict`.
