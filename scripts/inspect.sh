#!/usr/bin/env bash
# Launch the official MCP Inspector against our notes server.
#
# Inspector is Anthropic's official tool for exploring an MCP server in a
# browser UI: https://github.com/modelcontextprotocol/inspector
#
# Requires Node.js (it ships as `npx @modelcontextprotocol/inspector`).
# The first run will download the package; subsequent runs are instant.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"

# Use the project's venv python so the server has the `mcp` package available.
PYTHON="$REPO/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "venv not found. Run 'uv sync' first." >&2
  exit 1
fi

exec npx -y @modelcontextprotocol/inspector "$PYTHON" "$REPO/server/notes_server.py"
