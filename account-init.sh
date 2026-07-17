#!/usr/bin/env bash
# account-init.sh — make a fleet account's CLAUDE_CONFIG_DIR a COMPLETE, non-divergent
# view of this harness, fully SILOED inside the repo. It never touches ~/.claude.
#
# The external fleet tooling creates .claude-private/accounts/<name>/ and pins
# CLAUDE_CONFIG_DIR. This script COMPLETES/REPAIRS that dir, idempotently:
#   - symlinks the loader dirs Claude Code reads from the config dir
#     (agents/ commands/ hooks/ skills/) back to this repo
#   - materializes settings.json from templates/account-settings.json, injecting the
#     local repo root (the ONLY machine-specific value; it is never committed)
#
# It deliberately does NOT create memory/ evals/ state/ bin/ lint/ autonomy.json in the
# account dir: the hooks and bin/harness reach those via the absolute repo path baked into
# the generated settings.json (ROOT = dirname(dirname(abspath(__file__)))). It does NOT
# symlink CLAUDE.md either — the kernel loads as PROJECT memory (cwd = repo); a config-dir
# copy would double-load it.
#
# Prefer running this in a plain shell. (Running it through an agent's Bash tool also works
# — the internal `ln` calls are subprocesses the PreToolUse guard does not inspect — but an
# agent invoking the raw `ln -s .../hooks ...` commands directly WOULD be blocked by the guard.)
#
# Usage:
#   ./account-init.sh                          # repair the account named by $CLAUDE_CONFIG_DIR
#   ./account-init.sh <name>                   # init/repair .claude-private/accounts/<name>
#   ./account-init.sh [name] --sync-settings   # also (re)generate settings.json (backs up first)
#   ./account-init.sh <name> --store-account <name>  # choose/persist the shared-store owner
#   ./account-init.sh --all [--sync-settings]  # repair/sync EVERY account in lock-step (keeps
#                                              # all profiles' settings.json synced to the template)
#
# provenance: session 56295237, 2026-06-13 — fleet-config silo restructure (Stage 1).
set -euo pipefail

# Account settings, session transcripts, and local harness ledgers may contain prompt
# excerpts and machine paths. New files created by this installer must be owner-only;
# explicit chmod calls below also tighten the containing directories when possible.
umask 077

# Force REAL (native) symlinks on Windows/Git-Bash. Default MSYS `ln -s` silently deep-COPIES
# a directory, which would defeat the entire point (each account would diverge from the repo).
# `nativestrict` fails loudly instead of copying if symlink privilege is missing (enable
# Windows Developer Mode). No-op on Linux/macOS, where `ln -s` already makes real symlinks.
export MSYS=winsymlinks:nativestrict

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Native (e.g. Windows D:/...) form for the paths baked into settings.json, so the
# hook/statusLine commands resolve when Claude Code runs them.
if command -v cygpath >/dev/null 2>&1; then
  REPO_NATIVE="$(cygpath -m "$REPO_DIR")"
else
  REPO_NATIVE="$REPO_DIR"
fi

NAME=""
SYNC_SETTINGS=0
ALL=0
STORE_ACCOUNT_ARG=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --sync-settings) SYNC_SETTINGS=1 ;;
    --all) ALL=1 ;;
    --store-account)
      shift
      [ "$#" -gt 0 ] || { echo "ERROR: --store-account requires a name." >&2; exit 2; }
      STORE_ACCOUNT_ARG="$1"
      ;;
    --store-account=*) STORE_ACCOUNT_ARG="${1#*=}" ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *)
      [ -z "$NAME" ] || { echo "ERROR: pass only one account name." >&2; exit 2; }
      NAME="$1"
      ;;
  esac
  shift
done

valid_account_name() {
  [ -n "$1" ] || return 1
  case "$1" in -*|.|*/*|*\\*|*..*|*[!A-Za-z0-9._-]*) return 1 ;; esac
  return 0
}

if [ -n "$NAME" ] && ! valid_account_name "$NAME"; then
  echo "ERROR: invalid account name '$NAME' (non-empty; no '/', '\\', or '..')." >&2
  exit 2
fi
if [ -n "$STORE_ACCOUNT_ARG" ] && ! valid_account_name "$STORE_ACCOUNT_ARG"; then
  echo "ERROR: invalid store account '$STORE_ACCOUNT_ARG' (non-empty; no '/', '\\', or '..')." >&2
  exit 2
fi

# --all: repair/sync EVERY account under .claude-private/accounts/ in one pass, so all
# profiles stay in lock-step with the canonical template. Drift happens when the template
# advances and only one account is re-synced (settings.json is materialized per-account, not
# symlinked — by design, to allow per-account overrides.json). Re-execs this script per account.
# provenance (--all): session b46882f7, 2026-06-25 - keep all fleet profiles' settings in lock-step.
if [ "$ALL" -eq 1 ]; then
  [ -n "$NAME" ] && { echo "ERROR: --all cannot be combined with an account name." >&2; exit 2; }
  rc=0
  shopt -s nullglob
  for d in "$REPO_DIR"/.claude-private/accounts/*/; do
    acct="$(basename "$d")"
    case "$acct" in -*) echo "  SKIP $acct (account name starts with '-')" >&2; rc=1; continue ;; esac
    echo "========== $acct =========="
    store_args=()
    [ -n "$STORE_ACCOUNT_ARG" ] && store_args=(--store-account "$STORE_ACCOUNT_ARG")
    if [ "$SYNC_SETTINGS" -eq 1 ]; then
      bash "${BASH_SOURCE[0]}" "$acct" --sync-settings "${store_args[@]}" || rc=1
    else
      bash "${BASH_SOURCE[0]}" "$acct" "${store_args[@]}" || rc=1
    fi
  done
  exit $rc
fi

# Resolve the target account config dir WITHOUT mutating anything outside the silo.
if [ -n "$NAME" ]; then
  TARGET="$REPO_DIR/.claude-private/accounts/$NAME"
  mkdir -p "$TARGET"   # safe: inside the silo by construction
elif [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
  if command -v cygpath >/dev/null 2>&1; then TARGET="$(cygpath -u "$CLAUDE_CONFIG_DIR")"; else TARGET="$CLAUDE_CONFIG_DIR"; fi
  [ -d "$TARGET" ] || { echo "ERROR: CLAUDE_CONFIG_DIR '$TARGET' does not exist (fleet tooling should create it)." >&2; exit 2; }
else
  echo "ERROR: pass an account <name> or run with CLAUDE_CONFIG_DIR set." >&2; exit 2
fi
TARGET="$(cd "$TARGET" && pwd)"
PRIV="$(cd "$REPO_DIR/.claude-private" && pwd)"

# --- SAFETY GATE: only ever operate inside the repo's .claude-private; never ~/.claude ---
case "$TARGET/" in
  "$PRIV/"*) : ;;  # ok — inside the repo silo
  *) echo "REFUSING: '$TARGET' is not under '$PRIV'. The harness stays siloed; it will not touch global config." >&2; exit 1 ;;
esac
if [ "$TARGET" = "$(cd "$HOME" 2>/dev/null && pwd)/.claude" ]; then
  echo "REFUSING: target resolves to ~/.claude (global config). Aborting." >&2; exit 1
fi

# The directory boundary protects existing contents too, including state files that
# may have been created under a more permissive process umask. chmod can be advisory
# on some Windows filesystems, so PRIVACY.md also calls out the host ACL boundary.
chmod 700 "$PRIV" "$(dirname "$TARGET")" "$TARGET" 2>/dev/null || true
if [ -d "$REPO_DIR/state" ]; then chmod 700 "$REPO_DIR/state" 2>/dev/null || true; fi

# provenance: 2026-07-17 security/productization review — remove maintainer-specific defaults.
# Resolve and validate the shared-store choice before creating links or settings. Once a
# store is in use, changing it is a migration (sync + cutover), not an initialization flag.
ACCT_NAME="$(basename "$TARGET")"
STORE_CONFIG="$PRIV/session-store-account"
STORE_ACCOUNT=""
REQUESTED_STORE="${STORE_ACCOUNT_ARG:-${HARNESS_STORE_ACCOUNT:-}}"
if [ -L "$STORE_CONFIG" ] || { [ -e "$STORE_CONFIG" ] && [ ! -f "$STORE_CONFIG" ]; }; then
  echo "REFUSING: $STORE_CONFIG is not a regular file." >&2
  exit 1
fi
if [ -f "$STORE_CONFIG" ]; then
  STORE_ACCOUNT="$(cat "$STORE_CONFIG")"
  if ! valid_account_name "$STORE_ACCOUNT"; then
    echo "ERROR: invalid shared-store account in $STORE_CONFIG." >&2
    exit 2
  fi
  if [ -n "$REQUESTED_STORE" ] && [ "$REQUESTED_STORE" != "$STORE_ACCOUNT" ]; then
    echo "REFUSING: shared-store owner is already '$STORE_ACCOUNT'; requested '$REQUESTED_STORE'." >&2
    echo "Consolidate session stores and links before changing $STORE_CONFIG." >&2
    exit 1
  fi
elif [ -n "$REQUESTED_STORE" ]; then
  STORE_ACCOUNT="$REQUESTED_STORE"
elif [ -d "$REPO_DIR/.claude-private/accounts/rhen/projects" ]; then
  # One-time compatibility migration for pre-config installs; new installs choose the
  # first account they initialize instead of inheriting a maintainer-specific name.
  STORE_ACCOUNT="rhen"
else
  STORE_ACCOUNT="$ACCT_NAME"
fi
if ! valid_account_name "$STORE_ACCOUNT"; then
  echo "ERROR: invalid shared-store account '$STORE_ACCOUNT' from CLI, env, or $STORE_CONFIG." >&2
  exit 2
fi
if [ ! -f "$STORE_CONFIG" ]; then
  STORE_CONFIG_TMP="$STORE_CONFIG.tmp.$$"
  printf '%s\n' "$STORE_ACCOUNT" > "$STORE_CONFIG_TMP"
  chmod 600 "$STORE_CONFIG_TMP" 2>/dev/null || true
  mv "$STORE_CONFIG_TMP" "$STORE_CONFIG"
fi

echo "Account dir   : $TARGET"
echo "Repo (native) : $REPO_NATIVE"

# --- Idempotent symlinks: the dirs Claude Code loads from the config dir ---
link() {  # link <name>  (same name in repo and target)
  local src="$REPO_DIR/$1" dst="$TARGET/$1"
  if [ -L "$dst" ]; then
    if [ "$(readlink "$dst")" = "$src" ]; then echo "  ok    $1"; return; fi
    rm "$dst"; ln -s "$src" "$dst"; echo "  fixed $1"
  elif [ -e "$dst" ]; then
    echo "  SKIP  $1 (a real file/dir exists there — not overwriting)"
  else
    ln -s "$src" "$dst"; echo "  link  $1"
  fi
}
echo "Symlinks:"
link agents
link commands
link hooks
link skills

# --- Shared session store: every account reads/writes ONE projects/ so /resume
# sees sessions across accounts (ADR 0004). Unlike the four brain dirs (which link
# to the TRUNK), projects/ links to a locally selected canonical account. The choice
# is persisted inside the ignored/private silo so hooks and later runs agree. New/empty accounts auto-link here. An account
# whose projects/ is already a populated REAL dir is left untouched with a warning:
# consolidating it needs a lossless merge + a cutover that can't run while a session
# of that account is live — see ./sync-account-sessions.sh.
STORE="$REPO_DIR/.claude-private/accounts/$STORE_ACCOUNT/projects"
STORE_ACCOUNT_DIR="$(dirname "$STORE")"
if [ -d "$STORE_ACCOUNT_DIR" ]; then
  STORE_ACCOUNT_DIR_REAL="$(cd "$STORE_ACCOUNT_DIR" && pwd)"
  case "$STORE_ACCOUNT_DIR_REAL/" in
    "$PRIV/"*) : ;;
    *) echo "REFUSING: canonical store account resolves outside '$PRIV'." >&2; exit 1 ;;
  esac
fi
if [ -L "$STORE" ] || { [ -e "$STORE" ] && [ ! -d "$STORE" ]; }; then
  echo "REFUSING: canonical store '$STORE' must be a real directory." >&2
  exit 1
fi
if [ "$ACCT_NAME" = "$STORE_ACCOUNT" ]; then
  mkdir -p "$STORE"
fi
if [ -d "$STORE" ]; then chmod 700 "$STORE" 2>/dev/null || true; fi
echo "Session store:"
if [ "$ACCT_NAME" = "$STORE_ACCOUNT" ]; then
  echo "  ok    projects/ (this account OWNS the canonical store)"
elif [ ! -d "$STORE" ]; then
  echo "  SKIP  projects/ (canonical store '$STORE_ACCOUNT/projects' does not exist yet)"
else
  dst="$TARGET/projects"
  if [ -L "$dst" ]; then
    if [ "$(readlink "$dst")" = "$STORE" ]; then echo "  ok    projects -> $STORE_ACCOUNT/projects"
    else rm "$dst"; ln -s "$STORE" "$dst"; echo "  fixed projects -> $STORE_ACCOUNT/projects"; fi
  elif [ -d "$dst" ] && [ -n "$(ls -A "$dst" 2>/dev/null)" ]; then
    echo "  WARN  projects/ is a populated real dir — NOT auto-linking (would risk session loss)."
    echo "        Consolidate with:  ./sync-account-sessions.sh $ACCT_NAME   (run with no live '$ACCT_NAME' session)"
  elif [ -e "$dst" ]; then
    if rmdir "$dst" 2>/dev/null; then ln -s "$STORE" "$dst"; echo "  link  projects -> $STORE_ACCOUNT/projects (was empty)"
    else echo "  SKIP  projects/ (a real file/dir exists — not overwriting)"; fi
  else
    ln -s "$STORE" "$dst"; echo "  link  projects -> $STORE_ACCOUNT/projects"
  fi
fi

# --- Materialize settings.json from the portable canonical ---
SETTINGS="$TARGET/settings.json"
TEMPLATE="$REPO_DIR/templates/account-settings.json"
OVERRIDES="$TARGET/overrides.json"
for account_file in "$SETTINGS" "$OVERRIDES"; do
  if [ -L "$account_file" ] || { [ -e "$account_file" ] && [ ! -f "$account_file" ]; }; then
    echo "REFUSING: account file '$account_file' must be a regular file." >&2
    exit 1
  fi
done
if [ -e "$SETTINGS" ] && [ "$SYNC_SETTINGS" -eq 0 ]; then
  echo "settings.json : exists — left as-is (pass --sync-settings to regenerate)."
else
  if [ -e "$SETTINGS" ]; then
    bak="$SETTINGS.pre-sync.$(date +%s).$$"
    cp "$SETTINGS" "$bak"
    chmod 600 "$bak" 2>/dev/null || true
    echo "settings.json : backed up -> $(basename "$bak")"
  fi
  python3 - "$TEMPLATE" "$SETTINGS" "$REPO_NATIVE" "$OVERRIDES" <<'PY'
import json, os, sys
template_path, out_path, repo_root, overrides_path = sys.argv[1:5]
raw = open(template_path, encoding="utf-8").read().replace("{{REPO_ROOT}}", repo_root)
data = json.loads(raw)
data.pop("_provenance", None)

def deep_merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base

if os.path.exists(overrides_path):
    deep_merge(data, json.load(open(overrides_path, encoding="utf-8")))
    print("  merged overrides.json")
tmp_path = f"{out_path}.tmp.{os.getpid()}"
with open(tmp_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
try:
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, out_path)
finally:
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
print("  wrote settings.json")
PY
fi

for private_file in "$SETTINGS" "$OVERRIDES"; do
  if [ -f "$private_file" ]; then chmod 600 "$private_file" 2>/dev/null || true; fi
done

echo "Done. Account '$(basename "$TARGET")' is a complete, siloed view of the harness."
