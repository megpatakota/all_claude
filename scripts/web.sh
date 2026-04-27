#!/usr/bin/env bash
# Launch the FastAPI chat UI for the notes MCP server.
#
# Opens at http://localhost:8000 — type a message, watch the model call
# tools on notes_server.py.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

if [[ ! -x ".venv/bin/uvicorn" ]]; then
  echo "uvicorn not installed. Run 'uv sync' first." >&2
  exit 1
fi

exec .venv/bin/uvicorn web.app:app --reload --port 8000
