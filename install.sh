#!/usr/bin/env bash
# Install the harness as the user-scope Claude Code config (~/.claude).
# User scope = every project on this machine shares ONE brain. That is the point.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

if [ -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
  BACKUP="$TARGET.pre-harness.$(date +%s)"
  echo "Existing $TARGET found — backing up to $BACKUP"
  mv "$TARGET" "$BACKUP"
  # Preserve any prior user memory/settings the human may want to hand-merge.
  echo "NOTE: review $BACKUP for settings/memories to merge by hand."
fi

if [ -L "$TARGET" ]; then rm "$TARGET"; fi
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
echo "Installed: $TARGET -> $REPO_DIR"
echo "Next: run ./project-init.sh inside each project you work on."
