#!/usr/bin/env bash
# install.sh — harness installer.
#
# DEFAULT (fleet / siloed): this harness is consumed per-account via config dirs under
# .claude-private/accounts/<name>/ — created by the fleet tooling, completed by
# ./account-init.sh. NOTHING here touches the OS-global ~/.claude. Use:
#     ./account-init.sh <name>     # init/repair an account dir
#     ./account-init.sh            # inside a fleet session (uses $CLAUDE_CONFIG_DIR)
#
# LEGACY (single-user global): `./install.sh --global-legacy` symlinks the WHOLE repo to
# ~/.claude so every project on the machine shares it. It REPLACES ~/.claude, so it refuses
# if ~/.claude is already a real directory or if CLAUDE_CONFIG_DIR is set (a fleet).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "${1:-}" != "--global-legacy" ]; then
  cat <<EOF
Siloed/fleet model is the default — nothing is installed globally.
  • Init/repair an account:    ./account-init.sh <name>
  • Inside a fleet session:    ./account-init.sh           (uses \$CLAUDE_CONFIG_DIR)
  • Per-project thin contract: ./project-init.sh           (run in the project root)
  • Legacy single-user global (symlinks this repo to ~/.claude):
        ./install.sh --global-legacy
EOF
  python3 "$REPO_DIR/lint/lint_harness.py"   # a bare run stays a useful health check
  exit 0
fi

# --- legacy global model (opt-in, guarded so it can't clobber a real ~/.claude) ---
TARGET="$HOME/.claude"
if [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
  echo "REFUSING --global-legacy: CLAUDE_CONFIG_DIR is set ($CLAUDE_CONFIG_DIR). You are in a" >&2
  echo "fleet/siloed setup — use ./account-init.sh, not the global symlink." >&2
  exit 1
fi
if [ -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
  echo "REFUSING --global-legacy: $TARGET already exists as a real directory. Inspect/move it" >&2
  echo "by hand first; this script will not clobber a real global Claude config." >&2
  exit 1
fi
[ -L "$TARGET" ] && rm "$TARGET"
ln -s "$REPO_DIR" "$TARGET"
chmod +x "$REPO_DIR/bin/harness" "$REPO_DIR"/hooks/*.py
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$TARGET/bin"; then
  echo 'Add to your shell rc:  export PATH="$HOME/.claude/bin:$PATH"'
fi
cd "$REPO_DIR"
if [ ! -d .git ]; then
  git init -b main >/dev/null
  git add -A && git commit -m "harness v$(cat VERSION): initial install" >/dev/null
  echo "Initialized git repo. Add a remote:  git remote add origin <your-github-url>"
fi
python3 lint/lint_harness.py
echo "Installed (legacy global): $TARGET -> $REPO_DIR"
echo "Next: run ./project-init.sh inside each project you work on."
