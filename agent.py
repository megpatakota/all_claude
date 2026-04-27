"""Standalone agent: Claude API + our MCP server.

Walks the full agentic loop with every step printed:

  user prompt
    → Claude lists available MCP tools
    → Claude decides which tool(s) to call
    → MCP server executes the tool
    → result returns to Claude
    → Claude writes the final answer

What's wired together:
  - anthropic SDK (Claude API)
  - mcp SDK (talks to our notes_server.py over stdio)
  - anthropic.lib.tools.mcp.async_mcp_tool — adapter that lets Claude's
    tool runner invoke MCP tools transparently

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    uv run python agent.py
    uv run python agent.py "find notes about transports and add a TL;DR note"
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from anthropic import AsyncAnthropic
from anthropic.lib.tools.mcp import async_mcp_tool
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

load_dotenv()  # ANTHROPIC_API_KEY from .env at the repo root

SERVER = Path(__file__).resolve().parent / "server" / "notes_server.py"

DEFAULT_PROMPT = (
    "Search my notes for anything about MCP, then write me a 3-bullet summary "
    "citing each note by id. After that, add a new note titled "
    "'agent-run summary' whose body is your bullet summary."
)

MODEL = "claude-haiku-4-5"  # cheapest current Claude — $1/$5 per 1M tokens


def banner(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def render_block(block) -> None:
    """Pretty-print one content block from a Claude response."""
    btype = getattr(block, "type", None)
    if btype == "text":
        print(block.text)
    elif btype == "tool_use":
        print(f"[tool_use] {block.name}({block.input})")
    else:
        print(f"[{btype}] {block}")


def render_message(message) -> None:
    """Pretty-print one assistant message yielded by the tool runner."""
    banner(f"assistant turn (stop_reason={message.stop_reason})")
    for block in message.content:
        render_block(block)
    u = message.usage
    print(
        f"\n[usage] in={u.input_tokens} out={u.output_tokens} "
        f"cache_read={getattr(u, 'cache_read_input_tokens', 0)}"
    )


async def main() -> None:
    user_prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT

    banner("user prompt")
    print(user_prompt)

    claude = AsyncAnthropic()  # reads ANTHROPIC_API_KEY

    server_params = StdioServerParameters(
        command=sys.executable, args=[str(SERVER)]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as mcp_session:
            init = await mcp_session.initialize()
            banner("connected to MCP server")
            print(f"{init.serverInfo.name} v{init.serverInfo.version}")

            tools_result = await mcp_session.list_tools()
            banner("tools advertised to Claude")
            for t in tools_result.tools:
                print(f"- {t.name}: {t.description}")

            runner = claude.beta.messages.tool_runner(
                model=MODEL,
                max_tokens=4096,
                system=(
                    "You are a notes assistant. The user has an MCP-backed "
                    "notes knowledge base. Use the provided tools to answer "
                    "their request; cite note ids when you summarise."
                ),
                messages=[{"role": "user", "content": user_prompt}],
                tools=[async_mcp_tool(t, mcp_session) for t in tools_result.tools],
            )

            async for message in runner:
                render_message(message)

            banner("done")


if __name__ == "__main__":
    asyncio.run(main())
