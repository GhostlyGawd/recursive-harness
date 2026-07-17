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
for arg in "$@"; do
  case "$arg" in
    --sync-settings) SYNC_SETTINGS=1 ;;
    --all) ALL=1 ;;
    -*) echo "unknown flag: $arg" >&2; exit 2 ;;
    *) NAME="$arg" ;;
  esac
done

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
    if [ "$SYNC_SETTINGS" -eq 1 ]; then
      bash "${BASH_SOURCE[0]}" "$acct" --sync-settings || rc=1
    else
      bash "${BASH_SOURCE[0]}" "$acct" || rc=1
    fi
  done
  exit $rc
fi

# Resolve the target account config dir WITHOUT mutating anything outside the silo.
if [ -n "$NAME" ]; then
  case "$NAME" in */*|*..*) echo "ERROR: invalid account name '$NAME' (no '/' or '..')." >&2; exit 2 ;; esac
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
# to the TRUNK), projects/ links to the canonical store in the rhen account; rhen
# itself owns the real directory. New/empty accounts auto-link here. An account
# whose projects/ is already a populated REAL dir is left untouched with a warning:
# consolidating it needs a lossless merge + a cutover that can't run while a session
# of that account is live — see ./sync-account-sessions.sh.
STORE_ACCOUNT="rhen"
STORE="$REPO_DIR/.claude-private/accounts/$STORE_ACCOUNT/projects"
ACCT_NAME="$(basename "$TARGET")"
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
if [ -e "$SETTINGS" ] && [ "$SYNC_SETTINGS" -eq 0 ]; then
  echo "settings.json : exists — left as-is (pass --sync-settings to regenerate)."
else
  if [ -e "$SETTINGS" ]; then
    bak="$SETTINGS.pre-sync.$(date +%s)"
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
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print("  wrote settings.json")
PY
fi

for private_file in "$SETTINGS" "$OVERRIDES"; do
  if [ -f "$private_file" ]; then chmod 600 "$private_file" 2>/dev/null || true; fi
done

echo "Done. Account '$(basename "$TARGET")' is a complete, siloed view of the harness."
