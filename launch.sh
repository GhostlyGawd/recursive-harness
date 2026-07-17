#!/usr/bin/env bash
# Launch Claude Code with an explicit recursive-harness account silo.
# provenance: 2026-07-17 productization review — replace invisible shell-profile pins.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACCOUNT="${1:-}"
if [ -z "$ACCOUNT" ]; then
  echo "usage: ./launch.sh <account> [--] [claude arguments...]" >&2
  exit 2
fi
shift
[ "${1:-}" = "--" ] && shift

case "$ACCOUNT" in
  -*|.|*/*|*\\*|*..*|*[!A-Za-z0-9._-]*)
    echo "ERROR: invalid account '$ACCOUNT' (letters, numbers, '.', '_', and '-' only)." >&2
    exit 2
    ;;
esac

CONFIG_DIR="$REPO_DIR/.claude-private/accounts/$ACCOUNT"
if [ ! -d "$CONFIG_DIR" ] || [ ! -f "$CONFIG_DIR/settings.json" ]; then
  echo "ERROR: account '$ACCOUNT' is not initialized at $CONFIG_DIR." >&2
  echo "Run: ./account-init.sh '$ACCOUNT' --sync-settings" >&2
  exit 1
fi
CONFIG_DIR="$(cd "$CONFIG_DIR" && pwd)"

command -v claude >/dev/null 2>&1 || {
  echo "ERROR: 'claude' is not on PATH." >&2
  exit 127
}

export CLAUDE_CONFIG_DIR="$CONFIG_DIR"
printf 'Harness account : %s\n' "$ACCOUNT" >&2
printf 'Config directory: %s\n' "$CLAUDE_CONFIG_DIR" >&2
printf 'Checkout        : %s\n' "$REPO_DIR" >&2
exec claude "$@"
