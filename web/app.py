"""FastAPI chat UI for the notes MCP server.

Wraps `agent.py` as a web service:
  - GET  /          → serves the chat page
  - POST /chat      → runs one agent turn, streams events back as SSE

Each request spins up a fresh MCP session against notes_server.py. State
survives between requests because the server persists notes to JSON.

Run:
    uv run uvicorn web.app:app --reload --port 8000
    open http://localhost:8000
"""

from __future__ import annotations

import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path

from anthropic import AsyncAnthropic
from anthropic.lib.tools.mcp import async_mcp_tool
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import BaseModel

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = ROOT / "server" / "notes_server.py"
INDEX_HTML = Path(__file__).resolve().parent / "index.html"

MODEL = "claude-haiku-4-5"
SYSTEM = (
    "You are a notes assistant connected to an MCP-backed notes "
    "knowledge base. Use the provided tools to answer the user's "
    "request. When you summarise notes, cite them by id."
)

app = FastAPI()
claude = AsyncAnthropic()


class ChatRequest(BaseModel):
    prompt: str


def sse(event: dict) -> str:
    """Format an event as a Server-Sent Events frame."""
    return f"data: {json.dumps(event)}\n\n"


async def run_turn(prompt: str) -> AsyncIterator[str]:
    """Run one agent turn and stream events for the browser."""
    yield sse({"type": "status", "text": "connecting to MCP server"})

    server_params = StdioServerParameters(
        command=sys.executable, args=[str(SERVER_SCRIPT)]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as mcp_session:
            await mcp_session.initialize()
            tools_result = await mcp_session.list_tools()
            yield sse({"type": "status", "text": f"loaded {len(tools_result.tools)} tools"})

            runner = claude.beta.messages.tool_runner(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
                tools=[async_mcp_tool(t, mcp_session) for t in tools_result.tools],
            )

            async for message in runner:
                for block in message.content:
                    btype = getattr(block, "type", None)
                    if btype == "text":
                        yield sse({"type": "text", "text": block.text})
                    elif btype == "tool_use":
                        yield sse(
                            {"type": "tool_use", "name": block.name, "input": block.input}
                        )

            yield sse({"type": "done"})


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(run_turn(req.prompt), media_type="text/event-stream")
