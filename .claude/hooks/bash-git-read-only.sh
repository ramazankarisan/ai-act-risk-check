#!/usr/bin/env bash
# Bash allowlist for convention-reviewer: read-only git commands.
exec "$(dirname "$0")/allow-bash.sh" 'git (diff|log|show|status)( [^ ]+)*'
