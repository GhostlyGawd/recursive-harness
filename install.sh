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

# Install a repo-level managed post-merge dispatcher plus the harness-owned hook that keeps
# every fleet account's settings.json in lock-step with the template. A pre-existing custom
# post-merge hook is copied byte-for-byte into post-merge.d and executed by the dispatcher;
# it is never silently overwritten. Git hooks are not cloned, so every install repairs this
# wiring idempotently. Safe: account-init writes settings.json in place and backs up first.
# provenance: session b46882f7, 2026-06-26 - reproducible install of the fleet-settings auto-sync hook.
install_git_hooks() {
  command -v git >/dev/null 2>&1 || return 0
  git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1 || return 0
  local hooks_dir managed_dir managed_hook dispatcher preserved_hook
  hooks_dir="$(git -C "$REPO_DIR" rev-parse --git-path hooks)"
  command -v cygpath >/dev/null 2>&1 && hooks_dir="$(cygpath -u "$hooks_dir")"
  case "$hooks_dir" in
    /*) : ;;
    *) hooks_dir="$REPO_DIR/$hooks_dir" ;;
  esac
  managed_dir="$hooks_dir/post-merge.d"
  managed_hook="$managed_dir/50-recursive-harness"
  dispatcher="$hooks_dir/post-merge"
  preserved_hook="$managed_dir/10-existing-post-merge"
  if [ -L "$managed_dir" ] || { [ -e "$managed_dir" ] && [ ! -d "$managed_dir" ]; }; then
    echo "REFUSING: $managed_dir is not a regular directory." >&2
    return 1
  fi
  mkdir -p "$managed_dir"
  if [ -L "$managed_hook" ] || { [ -e "$managed_hook" ] && [ ! -f "$managed_hook" ]; }; then
    echo "REFUSING: $managed_hook is not a regular file." >&2
    return 1
  fi

  cat > "$managed_hook" <<'HOOK'
#!/usr/bin/env bash
# recursive-harness managed post-merge task: synchronize account settings after template changes.
set -uo pipefail
repo="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$repo" ] || exit 0
[ -f "$repo/account-init.sh" ] || exit 0
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
  chmod +x "$managed_hook"

  if [ -L "$dispatcher" ] || { [ -e "$dispatcher" ] && [ ! -f "$dispatcher" ]; }; then
    echo "REFUSING: $dispatcher is not a regular file; preserve and integrate it manually." >&2
    return 1
  fi
  if [ -f "$dispatcher" ] && ! grep -Fq '# recursive-harness managed post-merge dispatcher' "$dispatcher"; then
    # The old installer-owned single hook is superseded by the managed task above. Any other
    # hook is user-owned and must survive the migration exactly.
    if grep -Fq '# Installed by install.sh (git hooks are not cloned).' "$dispatcher"; then
      echo "Migrating the legacy recursive-harness post-merge hook to the managed dispatcher."
    elif [ -L "$preserved_hook" ] || { [ -e "$preserved_hook" ] && [ ! -f "$preserved_hook" ]; }; then
      echo "REFUSING: $preserved_hook is not a regular file." >&2
      return 1
    elif [ -e "$preserved_hook" ]; then
      if ! cmp -s "$dispatcher" "$preserved_hook"; then
        echo "REFUSING: both a custom post-merge hook and $preserved_hook exist with different contents." >&2
        echo "Reconcile them manually, then rerun ./install.sh." >&2
        return 1
      fi
    else
      cp -p "$dispatcher" "$preserved_hook"
      echo "Preserved existing post-merge hook: $preserved_hook"
    fi
  fi

  cat > "$dispatcher" <<'HOOK'
#!/usr/bin/env bash
# recursive-harness managed post-merge dispatcher
# Executes executable regular files in post-merge.d in lexical order.
set -uo pipefail
hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/post-merge.d"
status=0
for hook in "$hook_dir"/*; do
  [ -f "$hook" ] && [ ! -L "$hook" ] && [ -x "$hook" ] || continue
  "$hook" "$@"
  hook_status=$?
  if [ "$hook_status" -ne 0 ]; then
    echo "[post-merge] WARN: $(basename "$hook") exited $hook_status" >&2
    status="$hook_status"
  fi
done
exit "$status"
HOOK
  chmod +x "$dispatcher"
  echo "Git hooks installed: $dispatcher + $managed_hook"
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
