#!/usr/bin/env bash
# Remove Recursive Harness wiring without deleting the checkout, state, settings,
# transcripts, backups, or user-owned Git hooks.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACCOUNT=""
ALL_ACCOUNTS=0
REMOVE_GLOBAL=0

usage() {
  cat <<'EOF'
Usage: ./uninstall.sh [--account NAME | --all-accounts] [--global-legacy]

Always removes repository-owned post-merge hook wiring. Account options unlink
only Recursive Harness-managed links; settings, overrides, transcripts, state,
and the checkout are preserved. --global-legacy removes ~/.claude only when it
is a symlink to this checkout.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --account)
      shift
      [ "$#" -gt 0 ] || { echo "ERROR: --account requires a name." >&2; exit 2; }
      ACCOUNT="$1"
      ;;
    --account=*) ACCOUNT="${1#*=}" ;;
    --all-accounts) ALL_ACCOUNTS=1 ;;
    --global-legacy) REMOVE_GLOBAL=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument '$1'." >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ -n "$ACCOUNT" ] && [ "$ALL_ACCOUNTS" -eq 1 ]; then
  echo "ERROR: --account and --all-accounts are mutually exclusive." >&2
  exit 2
fi

valid_account_name() {
  [ -n "$1" ] || return 1
  case "$1" in -*|.|*/*|*\\*|*..*|*[!A-Za-z0-9._-]*) return 1 ;; esac
  return 0
}

remove_repo_hooks() {
  command -v git >/dev/null 2>&1 || return 0
  git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1 || return 0

  local hooks_dir managed_dir managed dispatcher preserved other_count
  hooks_dir="$(git -C "$REPO_DIR" rev-parse --git-path hooks)"
  command -v cygpath >/dev/null 2>&1 && hooks_dir="$(cygpath -u "$hooks_dir")"
  case "$hooks_dir" in /*) : ;; *) hooks_dir="$REPO_DIR/$hooks_dir" ;; esac
  managed_dir="$hooks_dir/post-merge.d"
  managed="$managed_dir/50-recursive-harness"
  dispatcher="$hooks_dir/post-merge"
  preserved="$managed_dir/10-existing-post-merge"

  if [ -L "$managed_dir" ] || { [ -e "$managed_dir" ] && [ ! -d "$managed_dir" ]; }; then
    echo "REFUSING: $managed_dir is not a regular directory." >&2
    return 1
  fi
  [ -f "$managed" ] && [ ! -L "$managed" ] && rm "$managed"

  other_count=0
  if [ -d "$managed_dir" ]; then
    for item in "$managed_dir"/*; do
      [ -e "$item" ] || continue
      [ "$item" = "$preserved" ] && continue
      other_count=$((other_count + 1))
    done
  fi

  if [ "$other_count" -eq 0 ] && [ -f "$preserved" ] && [ ! -L "$preserved" ]; then
    if [ -f "$dispatcher" ] && grep -Fq '# recursive-harness managed post-merge dispatcher' "$dispatcher"; then
      cp -p "$preserved" "$dispatcher"
      rm "$preserved"
      rmdir "$managed_dir" 2>/dev/null || true
      echo "Restored the pre-existing post-merge hook."
    else
      echo "Kept the preserved hook at $preserved because the dispatcher is no longer harness-owned."
    fi
  elif [ "$other_count" -eq 0 ]; then
    if [ -f "$dispatcher" ] && grep -Fq '# recursive-harness managed post-merge dispatcher' "$dispatcher"; then
      rm "$dispatcher"
    fi
    rmdir "$managed_dir" 2>/dev/null || true
    echo "Removed Recursive Harness Git-hook wiring."
  else
    echo "Removed the Recursive Harness post-merge task; kept the dispatcher for other tasks."
  fi
}

remove_account_links() {
  local name="$1" target link target_path
  valid_account_name "$name" || { echo "ERROR: invalid account name '$name'." >&2; return 2; }
  target="$REPO_DIR/.claude-private/accounts/$name"
  [ -d "$target" ] || { echo "SKIP  account '$name' does not exist."; return 0; }

  for link in agents commands hooks skills projects; do
    target_path="$target/$link"
    if [ -L "$target_path" ]; then
      rm "$target_path"
      echo "Unlinked account '$name': $link"
    elif [ -e "$target_path" ] && [ "$link" != projects ]; then
      echo "KEEP  account '$name': $link is not a symlink."
    fi
  done
  echo "Preserved account '$name' settings, overrides, transcripts, and backups."
}

remove_global_legacy() {
  local target="$HOME/.claude" resolved
  if [ ! -L "$target" ]; then
    echo "SKIP  $target is not a symlink."
    return 0
  fi
  resolved="$(cd "$target" 2>/dev/null && pwd -P || true)"
  if [ "$resolved" != "$REPO_DIR" ]; then
    echo "REFUSING: $target points to '$resolved', not this checkout." >&2
    return 1
  fi
  rm "$target"
  echo "Removed legacy global link: $target"
}

remove_repo_hooks

if [ -n "$ACCOUNT" ]; then
  remove_account_links "$ACCOUNT"
elif [ "$ALL_ACCOUNTS" -eq 1 ]; then
  shopt -s nullglob
  for account_dir in "$REPO_DIR"/.claude-private/accounts/*/; do
    remove_account_links "$(basename "$account_dir")"
  done
fi

[ "$REMOVE_GLOBAL" -eq 1 ] && remove_global_legacy

echo "Uninstall complete. Checkout, local state, settings, transcripts, and backups were not deleted."

