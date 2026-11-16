#!/usr/bin/env bash
# Bash allowlist for test-runner and test-writer: run checks only, never change files.
exec "$(dirname "$0")/allow-bash.sh" \
  'uv run (ruff check( [^ ]+)*|ruff format --check( [^ ]+)*|mypy( [^ ]+)*|pytest( [^ ]+)*)' \
  '--fix|--unsafe-fixes|--add-noqa|--watch|--config|--install-types|--output-file|--junitxml'
