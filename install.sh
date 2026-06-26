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

# Install the repo-level git hook that keeps every fleet account's settings.json in lock-step
# with the template. Drift is born when a pull/merge advances templates/account-settings.json and
# the accounts aren't re-materialized; this post-merge hook re-syncs ALL profiles right then.
# Git hooks are not cloned, so this re-creates it on every install (idempotent). Safe: account-init
# writes settings.json in place and backs up first.
install_git_hooks() {
  command -v git >/dev/null 2>&1 || return 0
  git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1 || return 0
  local hooks_dir
  hooks_dir="$(git -C "$REPO_DIR" config --get core.hooksPath || true)"
  if [ -n "$hooks_dir" ]; then
    command -v cygpath >/dev/null 2>&1 && hooks_dir="$(cygpath -u "$hooks_dir")"
  else
    hooks_dir="$(git -C "$REPO_DIR" rev-parse --absolute-git-dir)/hooks"
  fi
  mkdir -p "$hooks_dir"
  cat > "$hooks_dir/post-merge" <<'HOOK'
#!/usr/bin/env bash
# post-merge - auto-sync every fleet account's settings.json when the settings TEMPLATE changes.
# Installed by install.sh (git hooks are not cloned). Safe + idempotent: account-init.sh writes
# settings.json in place and backs up first, so re-running is harmless.
set -uo pipefail
repo="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$repo" ] || exit 0
# Files changed by the merge/pull just applied (ORIG_HEAD = pre-merge tip). If we can't tell,
# default to syncing (cheap + idempotent) rather than silently skipping.
changed="$(git diff --name-only ORIG_HEAD HEAD 2>/dev/null || true)"
if [ -z "$changed" ] || printf '%s\n' "$changed" | grep -q '^templates/account-settings\.json$'; then
  echo "[post-merge] settings template changed -> syncing all fleet profiles..."
  if bash "$repo/account-init.sh" --all --sync-settings; then
    echo "[post-merge] fleet settings synced."
  else
    echo "[post-merge] WARN: sync failed; run ./account-init.sh --all --sync-settings manually." >&2
  fi
fi
exit 0
HOOK
  chmod +x "$hooks_dir/post-merge"
  echo "Git hook installed: $hooks_dir/post-merge (auto-syncs fleet settings on template change)."
}

if [ "${1:-}" != "--global-legacy" ]; then
  cat <<EOF
Siloed/fleet model is the default — nothing is installed globally.
  • Init/repair an account:    ./account-init.sh <name>
  • Inside a fleet session:    ./account-init.sh           (uses \$CLAUDE_CONFIG_DIR)
  • Per-project thin contract: ./project-init.sh           (run in the project root)
  • Legacy single-user global (symlinks this repo to ~/.claude):
        ./install.sh --global-legacy
EOF
  install_git_hooks
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
install_git_hooks
python3 lint/lint_harness.py
echo "Installed (legacy global): $TARGET -> $REPO_DIR"
echo "Next: run ./project-init.sh inside each project you work on."
