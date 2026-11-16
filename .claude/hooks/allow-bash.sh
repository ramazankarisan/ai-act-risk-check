#!/usr/bin/env bash
# PreToolUse hook for subagents: allow a Bash command only if it matches one allowed pattern.
# Usage (in agent frontmatter): allow-bash.sh '<allowed regex>' ['<denied regex>']
# The optional denied regex blocks flags that would change files (e.g. ruff --fix).
# Rejects command chaining, redirection and substitution so an allowed prefix cannot be abused.
# Exit 2 blocks the call and shows the reason to the agent.
set -uo pipefail
command -v jq >/dev/null || { echo "Blocked: jq is required by this hook." >&2; exit 2; }

allowed_regex="${1:?allow-bash.sh needs an allowed-command regex}"
denied_regex="${2:-}"
cmd="$(jq -r '.tool_input.command // empty')"

if [[ "$cmd" =~ [\;\&\|\>\<\`] || "$cmd" == *'$('* || "$cmd" == *$'\n'* ]]; then
  echo "Blocked: chaining, pipes, redirection and substitution are not allowed for this agent." >&2
  exit 2
fi

if [[ -n "$denied_regex" && "$cmd" =~ $denied_regex ]]; then
  echo "Blocked: '$cmd' uses a flag this agent may not use: $denied_regex" >&2
  exit 2
fi

if [[ "$cmd" =~ ^($allowed_regex)$ ]]; then
  exit 0
fi

echo "Blocked: '$cmd' is not in this agent's allowed commands: $allowed_regex" >&2
exit 2
