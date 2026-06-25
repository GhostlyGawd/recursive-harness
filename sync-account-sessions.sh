#!/usr/bin/env bash
# sync-account-sessions.sh — consolidate ONE fleet account's session store into the
# shared canonical store, then symlink it, so /resume sees every session from either
# account (ADR 0004). Lossless: it never reduces the store — a longer shared transcript is
# taken only when the store copy is a strict byte-prefix of it (a pure append-continuation);
# a FORKED same-path copy is backed up (.forked.<ts>) before overwrite. It RENAMES the
# account's old projects/ to a .bak (never deletes), and refuses to cut over unless the
# store is already a complete superset of the account's sessions.
#
# Why a separate tool (not account-init.sh): converting a POPULATED projects/ requires
# (a) a careful merge — an account may hold the longer copy of a shared transcript — and
# (b) renaming projects/, which Windows blocks while a session of that account holds a
# file open under it. So this MUST run with no live session of the target account (a
# session of a DIFFERENT account, or a plain terminal, is fine).
#
# Usage:
#   ./sync-account-sessions.sh <account>     # e.g. wraith
#   ./sync-account-sessions.sh               # account = basename of $CLAUDE_CONFIG_DIR
#
# provenance: session b46882f7, 2026-06-25 — user runs rhen+wraith concurrently and wants
# /resume to span both; per-account projects/ had silently diverged (ADR 0004).
set -euo pipefail
export MSYS=winsymlinks:nativestrict   # force REAL native symlinks on Git-Bash (else it silently COPIES)

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACCTS="$REPO_DIR/.claude-private/accounts"
STORE_ACCOUNT="rhen"               # the account that OWNS the canonical physical store

NAME="${1:-}"
if [ -z "$NAME" ] && [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
  if command -v cygpath >/dev/null 2>&1; then NAME="$(basename "$(cygpath -u "$CLAUDE_CONFIG_DIR")")"; else NAME="$(basename "$CLAUDE_CONFIG_DIR")"; fi
fi
[ -n "$NAME" ] || { echo "ERROR: pass an account <name> or set CLAUDE_CONFIG_DIR." >&2; exit 2; }
case "$NAME" in */*|*..*) echo "ERROR: invalid account name '$NAME'." >&2; exit 2 ;; esac
[ "$NAME" = "$STORE_ACCOUNT" ] && { echo "Account '$NAME' OWNS the store; nothing to consolidate." >&2; exit 0; }

STORE="$ACCTS/$STORE_ACCOUNT/projects"
ACCT="$ACCTS/$NAME/projects"
[ -d "$STORE" ] || { echo "ERROR: canonical store missing: $STORE" >&2; exit 1; }

if [ -L "$ACCT" ]; then
  echo "$NAME/projects is already a symlink -> $(readlink "$ACCT"). Nothing to do."; exit 0
fi
[ -d "$ACCT" ] || { echo "ERROR: $NAME/projects missing: $ACCT" >&2; exit 1; }

echo "== Step 1: merge '$NAME' into '$STORE_ACCOUNT' store (add missing; take the longer copy of any shared transcript) =="
copied=0
cd "$ACCT"
while IFS= read -r f; do
  rel="${f#./}"; src="$ACCT/$rel"; dst="$STORE/$rel"
  if [ ! -e "$dst" ]; then
    mkdir -p "$(dirname "$dst")"; cp -p "$src" "$dst"; copied=$((copied+1)); echo "  + $rel"
  else
    ss=$(stat -c %s "$src"); ds=$(stat -c %s "$dst")
    if [ "$ss" -gt "$ds" ]; then
      if cmp -s "$dst" <(head -c "$ds" "$src"); then
        cp -p "$src" "$dst"; copied=$((copied+1)); echo "  ^ $rel (store + appended tail)"
      else
        bak="$dst.forked.$(date +%Y%m%d-%H%M%S)"; cp -p "$dst" "$bak"
        cp -p "$src" "$dst"; copied=$((copied+1))
        echo "  ! $rel (FORKED: store copy diverged — backed up store -> $(basename "$bak"), took '$NAME')"
      fi
    fi
  fi
done < <(find . -type f -name '*.jsonl')
echo "  merged $copied file(s)."

echo "== Step 2: safety gate — store must now contain every '$NAME' session by path =="
cd "$STORE" && find . -type f -name '*.jsonl' | sort > /tmp/_store_chk.$$
cd "$ACCT"  && find . -type f -name '*.jsonl' | sort > /tmp/_acct_chk.$$
missing=$(comm -13 /tmp/_store_chk.$$ /tmp/_acct_chk.$$ | wc -l)
rm -f /tmp/_store_chk.$$ /tmp/_acct_chk.$$
[ "$missing" -eq 0 ] || { echo "ABORT: $missing '$NAME' file(s) still not in the store." >&2; exit 1; }
echo "  OK — store is a complete superset of '$NAME'."

echo "== Step 3: park '$NAME/projects' and symlink it to the shared store =="
ts=$(date +%Y%m%d-%H%M%S)
mv "$ACCT" "$ACCT.bak.$ts"   # FAILS if a '$NAME' session is live (open-file lock) — that is the guard.
ln -s "$STORE" "$ACCT"
if [ -L "$ACCT" ] && [ "$(readlink "$ACCT")" = "$STORE" ]; then
  echo "  linked: $NAME/projects -> $STORE_ACCOUNT/projects"
else
  echo "ERROR: symlink not created (MSYS copied instead? enable Windows Developer Mode). Restoring." >&2
  rm -rf "$ACCT"; mv "$ACCT.bak.$ts" "$ACCT"; exit 1
fi

# tidy a dead fossil link from the previous (severed) topology, if present
OLD="$ACCTS/$STORE_ACCOUNT/projects.oldlink"
[ -L "$OLD" ] && { rm -f "$OLD"; echo "  removed stale fossil: $STORE_ACCOUNT/projects.oldlink"; }

echo
echo "DONE. '$NAME' and '$STORE_ACCOUNT' now share one session store ($STORE)."
echo "Parked copy: $ACCT.bak.$ts  (delete once /resume from '$NAME' is confirmed)."