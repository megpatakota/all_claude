"""End-to-end MCP client journey.

Spawns the FastMCP server over stdio and exercises every primitive:
  1. list & call tools  (add_note, search_notes, delete_note)
  2. list & read resources  (notes://list, notes://{id})
  3. list & get prompts  (summarize_notes, daily_review)

Run:
    uv run python client/journey.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent.parent / "server" / "notes_server.py"


def banner(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            banner("initialize")
            print(f"server: {init.serverInfo.name} v{init.serverInfo.version}")
            print(f"capabilities: {init.capabilities.model_dump(exclude_none=True)}")

            # ---- TOOLS ---------------------------------------------------
            banner("tools/list")
            tools = await session.list_tools()
            for t in tools.tools:
                print(f"- {t.name}: {t.description}")

            banner("tools/call add_note")
            created = await session.call_tool(
                "add_note",
                {
                    "title": "MCP transports",
                    "body": "stdio for local, HTTP streaming for remote.",
                    "tags": ["mcp", "transport"],
                },
            )
            print(created.content[0].text)

            banner("tools/call search_notes")
            found = await session.call_tool("search_notes", {"query": "mcp"})
            print(found.content[0].text)

            # ---- RESOURCES -----------------------------------------------
            banner("resources/list")
            resources = await session.list_resources()
            for r in resources.resources:
                print(f"- {r.uri}  ({r.name})")

            banner("resources/templates/list")
            templates = await session.list_resource_templates()
            for tpl in templates.resourceTemplates:
                print(f"- {tpl.uriTemplate}  ({tpl.name})")

            banner("resources/read notes://list")
            listing = await session.read_resource("notes://list")
            print(listing.contents[0].text)

            banner("resources/read notes://1")
            note = await session.read_resource("notes://1")
            print(note.contents[0].text)

            # ---- PROMPTS -------------------------------------------------
            banner("prompts/list")
            prompts = await session.list_prompts()
            for p in prompts.prompts:
                print(f"- {p.name}: {p.description}")

            banner("prompts/get summarize_notes")
            got = await session.get_prompt("summarize_notes", {"topic": "mcp"})
            for msg in got.messages:
                print(f"[{msg.role}] {msg.content.text}")

            banner("prompts/get daily_review")
            got = await session.get_prompt("daily_review", {})
            for msg in got.messages:
                print(f"[{msg.role}] {msg.content.text}")

            # ---- TEARDOWN ------------------------------------------------
            banner("tools/call delete_note")
            removed = await session.call_tool("delete_note", {"note_id": 1})
            print(removed.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
