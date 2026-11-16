#!/usr/bin/env bash
# Claude Code PostToolUse hook: format and lint-fix any Python file Claude just edited.
# Input: tool-call JSON on stdin. Never blocks; remaining lint errors are reported back to Claude.
set -uo pipefail

file_path="$(jq -r '.tool_input.file_path // empty')"
[[ "$file_path" == *.py && -f "$file_path" ]] || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
uv run --quiet ruff format --quiet "$file_path"
if ! output="$(uv run --quiet ruff check --fix --quiet "$file_path" 2>&1)"; then
  echo "ruff found issues it could not auto-fix in $file_path:" >&2
  echo "$output" >&2
  exit 2 # exit 2 shows stderr to Claude so it fixes them
fi
exit 0
