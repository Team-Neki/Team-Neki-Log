#!/usr/bin/env bash
# PostToolUse hook: run ruff on edited Python files under aggregation/.
# Best-effort — always exits 0 so a missing tool or lint error never blocks Claude.

set -u

payload="$(cat || true)"
[ -z "$payload" ] && exit 0

file_path="$(
  python3 - <<'PY' "$payload"
import json, sys
try:
    data = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
print(data.get("tool_input", {}).get("file_path", ""))
PY
)"

case "$file_path" in
  *.py) ;;
  *) exit 0 ;;
esac

case "$file_path" in
  */aggregation/*) ;;
  *) exit 0 ;;
esac

[ -f "$file_path" ] || exit 0
command -v ruff >/dev/null 2>&1 || exit 0

ruff check --fix --quiet "$file_path" >/dev/null 2>&1 || true
ruff format --quiet "$file_path" >/dev/null 2>&1 || true
exit 0
