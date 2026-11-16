#!/usr/bin/env bash
# PreToolUse hook for subagents: allow Edit/Write only inside the given project-relative directories.
# Usage (in agent frontmatter): allow-paths.sh tests [other-dir ...]
# Exit 2 blocks the call and shows the reason to the agent.
set -uo pipefail
command -v jq >/dev/null || { echo "Blocked: jq is required by this hook." >&2; exit 2; }

project_dir="$(cd "${CLAUDE_PROJECT_DIR:-.}" && pwd -P)"
file_path="$(jq -r '.tool_input.file_path // empty')"
[[ -n "$file_path" ]] || { echo "Blocked: no file_path in tool input." >&2; exit 2; }
[[ "$file_path" = /* ]] || file_path="$project_dir/$file_path"

# Resolve the nearest existing ancestor to defeat ../ and symlink tricks
# (the file and its new subdirectories may not exist yet).
existing="$(dirname "$file_path")"
rest="$(basename "$file_path")"
while [[ ! -d "$existing" ]]; do
  rest="$(basename "$existing")/$rest"
  existing="$(dirname "$existing")"
done
if [[ "$rest" == *..* ]]; then
  echo "Blocked: '..' is not allowed in new path segments." >&2
  exit 2
fi
resolved="$(cd "$existing" && pwd -P)/$rest"

for dir in "$@"; do
  if [[ "$resolved" == "$project_dir/$dir/"* ]]; then
    exit 0
  fi
done

echo "Blocked: this agent may only write inside: $* (got ${resolved#"$project_dir"/})" >&2
exit 2
