#!/usr/bin/env bash
# Pre-tool hook: audit all tool calls and block dangerous operations.
# Receives tool name on $1 and full input JSON on stdin.
# Writes to data/logs/audit.jsonl (creates parent dir if needed).
# Exits non-zero to BLOCK the tool call; exits 0 to allow it.

TOOL_NAME="${1:-unknown}"
INPUT_JSON="$(cat)"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${DATA_DIR:-$REPO_ROOT/data}/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\n' "{\"timestamp\":\"$TIMESTAMP\",\"tool\":\"$TOOL_NAME\",\"input\":$(echo "$INPUT_JSON" | tr -d '\n')}" >> "$LOG_DIR/audit.jsonl"

# Block rm -rf
if echo "$INPUT_JSON" | grep -qE '"command".*rm[[:space:]]+-[a-z]*r[a-z]*f|rm[[:space:]]+-[a-z]*f[a-z]*r'; then
  echo "BLOCKED: rm -rf is not allowed in this workspace." >&2
  exit 2
fi

# Block writes to .env files
if [[ "$TOOL_NAME" == "Write" ]] || [[ "$TOOL_NAME" == "Edit" ]]; then
  if echo "$INPUT_JSON" | grep -qE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*\.env[^"]*"'; then
    echo "BLOCKED: writes to .env files are not allowed." >&2
    exit 2
  fi
fi

# Block sudo
if echo "$INPUT_JSON" | grep -qE '"command".*\bsudo\b'; then
  echo "BLOCKED: sudo is not allowed in this workspace." >&2
  exit 2
fi

exit 0
