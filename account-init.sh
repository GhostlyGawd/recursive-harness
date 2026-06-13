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
#
# provenance: session 56295237, 2026-06-13 — fleet-config silo restructure (Stage 1).
set -euo pipefail

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
for arg in "$@"; do
  case "$arg" in
    --sync-settings) SYNC_SETTINGS=1 ;;
    -*) echo "unknown flag: $arg" >&2; exit 2 ;;
    *) NAME="$arg" ;;
  esac
done

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

echo "Done. Account '$(basename "$TARGET")' is a complete, siloed view of the harness."
