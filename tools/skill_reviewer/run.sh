#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/Users/sakana/PyEnv/prompt-engineering}"

cd "${PROJECT_ROOT}"

echo "Skill reviewer starting..."
echo "URL: http://127.0.0.1:8765"
echo "Close this terminal or press Ctrl+C to stop."
echo

exec uv run python tools/skill_reviewer/server.py --port 8765
