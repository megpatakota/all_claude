"""FastMCP server: a small notes knowledge base.

Exposes the three core MCP primitives from the "Future of MCP" talk:
  - tools     : callable functions the agent can invoke
  - resources : data the agent can read by URI
  - prompts   : reusable prompt templates the user/agent can fill in

Run directly over stdio:
    uv run python server/notes_server.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notes-kb")

STORE = Path(__file__).resolve().parent / "notes_store.json"

SEED: dict[str, dict[str, Any]] = {
    "1": {
        "id": 1,
        "title": "MCP primitives",
        "body": "Tools, resources, and prompts are the three foundational MCP primitives.",
        "tags": ["mcp", "intro"],
        "created_at": "2026-04-20T09:00:00Z",
    },
    "2": {
        "id": 2,
        "title": "Why MCP matters",
        "body": "MCP standardises how AI applications connect to data and tools.",
        "tags": ["mcp", "rationale"],
        "created_at": "2026-04-21T10:30:00Z",
    },
}


def _load() -> dict[int, dict[str, Any]]:
    if not STORE.exists():
        STORE.write_text(json.dumps(SEED, indent=2))
    raw = json.loads(STORE.read_text())
    return {int(k): v for k, v in raw.items()}


def _save(notes: dict[int, dict[str, Any]]) -> None:
    STORE.write_text(json.dumps({str(k): v for k, v in notes.items()}, indent=2))


def _next_id(notes: dict[int, dict[str, Any]]) -> int:
    return (max(notes) if notes else 0) + 1


@mcp.tool()
def add_note(title: str, body: str, tags: list[str] | None = None) -> dict[str, Any]:
    """Create a new note. Returns the stored note including its assigned id."""
    notes = _load()
    nid = _next_id(notes)
    note = {
        "id": nid,
        "title": title,
        "body": body,
        "tags": tags or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    notes[nid] = note
    _save(notes)
    return note


@mcp.tool()
def search_notes(query: str) -> list[dict[str, Any]]:
    """Case-insensitive substring search across note title, body, and tags."""
    notes = _load()
    q = query.lower().strip()
    if not q:
        return list(notes.values())
    hits = []
    for note in notes.values():
        haystack = " ".join([note["title"], note["body"], " ".join(note["tags"])]).lower()
        if q in haystack:
            hits.append(note)
    return hits


@mcp.tool()
def delete_note(note_id: int) -> dict[str, Any]:
    """Delete a note by id. Returns {deleted: true|false, id: ...}."""
    notes = _load()
    removed = notes.pop(note_id, None)
    _save(notes)
    return {"deleted": removed is not None, "id": note_id}


@mcp.resource("notes://list")
def list_notes() -> str:
    """A plain-text index of every note (id, title, tags)."""
    notes = _load()
    if not notes:
        return "(no notes)"
    lines = [f"{n['id']:>3}  {n['title']}  [{', '.join(n['tags'])}]" for n in notes.values()]
    return "\n".join(lines)


@mcp.resource("notes://{note_id}")
def get_note(note_id: str) -> str:
    """Full body of a single note, addressed by id."""
    try:
        nid = int(note_id)
    except ValueError:
        return f"invalid note id: {note_id!r}"
    note = _load().get(nid)
    if note is None:
        return f"note {nid} not found"
    return (
        f"# {note['title']}\n"
        f"_id: {note['id']} | created: {note['created_at']} | tags: {', '.join(note['tags'])}_\n\n"
        f"{note['body']}"
    )


@mcp.prompt()
def summarize_notes(topic: str) -> str:
    """Prompt the model to summarise notes matching a topic."""
    return (
        f"Using the `search_notes` tool, find notes related to '{topic}', "
        "then write a tight 3-bullet summary citing each note by id."
    )


@mcp.prompt()
def daily_review() -> str:
    """A reusable end-of-day review prompt."""
    return (
        "Read the `notes://list` resource, then for each note give one sentence on "
        "whether it still feels relevant today. Suggest one note to delete."
    )


if __name__ == "__main__":
    mcp.run()
