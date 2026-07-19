#!/usr/bin/env bash
# Compatibility wrapper retained for operators who used the former initializer.
# It is deliberately read-only: existing repository configuration is authoritative.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

echo "project-init no longer edits CLAUDE.md or any repository file." >&2
echo "Existing repository configuration remains authoritative." >&2
exec python3 "$SCRIPT_DIR/scripts/recursive_inspect.py" "$PWD" "$@"
