#!/usr/bin/env python3
"""PostToolUse hook (matcher: Bash|Edit|Write|MultiEdit): silently capture tool
FAILURES into a per-repo candidates stream, so the auto-healer ledger is seeded
without depending on the agent remembering to run `heal.py fix`.

Capture is candidates-ONLY: it appends to state/heal/<repo-key>/candidates.jsonl,
NEVER to bugs.jsonl. Promotion to a durable bug stays a reviewed, agent-initiated
pull (`heal.py promote <signature>`), so raw auto-capture noise can never inflate
the healed-bug metric and no-auto-memory (ADR 0001) is preserved.

Dark by default: gated by the SOFT flag observability.heal_autocapture (default
false, ADR 0008). Fail-open and ASCII-safe: any error -> exit 0, never blocks a tool.

provenance: 2026-06-26, session 689f12f4 - followup db6750
(proposal 2026-06-21-auto-healer-v2-locked-items.md, item 1).
"""
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys

try:
    from harness_features import flag
except Exception:  # never let a config-reader import brick the hook
    def flag(key, default=None):
        return default

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HARNESS_ROOT)
import private_state
HEAL_DIR = os.path.join(HARNESS_ROOT, "state", "heal")

# Failure signals in tool output. Generous ON PURPOSE: a false positive only seeds a
# candidate, never a bug (promotion is a reviewed pull). Traceback / pytest-style
# FAILED / assertion / generic error: / non-zero exit phrasing.
_FAIL_RE = re.compile(
    r"Traceback \(most recent call last\)|\bFAILED\b|\bAssertionError\b"
    r"|\bError:|\berror:|\bFAIL\b|exit(?:ed)?(?: code| with)? [1-9]|non-zero exit",
    re.IGNORECASE)
# Tokens stripped before signing so the SAME failure "in a different shape" collapses to
# ONE signature: hex addrs, bare numbers (line:col), quoted strings, win/posix path frags.
_VOLATILE_RE = re.compile(
    r"0x[0-9a-fA-F]+|[0-9]+|['\"][^'\"]*['\"]|[A-Za-z]:[\\/][^\s]*|/[^\s]*")


def _text_and_code(resp):
    """Normalize a tool_response (dict | str | other) to (searchable_text, exit_code|None)."""
    code = None
    if isinstance(resp, dict):
        for k in ("exit_code", "returncode", "exitCode", "code", "status"):
            v = resp.get(k)
            if isinstance(v, int):
                code = v
                break
        parts = [v for k in ("stdout", "stderr", "output", "error", "content",
                             "result", "message")
                 for v in (resp.get(k),) if isinstance(v, str)]
        text = "\n".join(parts) if parts else json.dumps(resp, ensure_ascii=False)
    elif isinstance(resp, str):
        text = resp
    else:
        text = "" if resp is None else str(resp)
    return text, code


def _salient_line(text):
    """First failure-matching line, else last non-empty line; clipped to 200 ASCII chars."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    sal = ""
    for ln in lines:
        if _FAIL_RE.search(ln):
            sal = ln
            break
    if not sal:
        sal = lines[-1] if lines else ""
    return sal.encode("ascii", "replace").decode("ascii")[:200]


def _signature(salient):
    """Stable 12-hex signature of the salient line with volatile tokens stripped, so the
    same root failure dedupes across paths/line-numbers (the count>=2 promote signal)."""
    norm = re.sub(r"\s+", " ", _VOLATILE_RE.sub("", salient)).strip().lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def _repo_key(cwd):
    """Per-repo ledger key. MIRRORS skills/auto-healer/heal.py _repo_key (single source of
    the algorithm): <basename>-<6 hex sha1 of the normcased git-toplevel abspath. The
    abspath is hashed (not os.path.relpath, which raises across drive letters on Windows).
    Keep in sync with that helper if the keying ever changes."""
    base_dir = cwd or os.getcwd()
    top = base_dir
    try:
        r = subprocess.run(["git", "-C", base_dir, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            top = r.stdout.strip()
    except Exception:
        pass
    top = os.path.abspath(top)
    base = os.path.basename(top.rstrip("/\\")) or "repo"
    h = hashlib.sha1(os.path.normcase(top).encode("utf-8")).hexdigest()[:6]
    return f"{base}-{h}"


def main() -> int:
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal 2026-06-23-utf8-stdout-all-entrypoints).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    # SOFT flag (ADR 0008): ships DARK. No capture unless a human turns it on.
    if not flag("observability.heal_autocapture", False):
        return 0
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, ValueError):
        return 0
    if not isinstance(data, dict):
        return 0
    text, code = _text_and_code(data.get("tool_response"))
    if not ((isinstance(code, int) and code != 0) or _FAIL_RE.search(text)):
        return 0  # not a failure -> nothing to seed
    try:
        salient = _salient_line(text)
        if not salient:
            return 0
        repo = _repo_key(data.get("cwd"))
        rec = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "repo": repo,
            "signature": _signature(salient),
            "snippet": salient,
            "tool": data.get("tool_name", "?"),
            "session": data.get("session_id", "?"),
        }
        path = os.path.join(HEAL_DIR, repo, "candidates.jsonl")
        private_state.append_jsonl(path, rec)
    except (OSError, ValueError, KeyError, AttributeError):
        return 0  # fail-open: never block or slow a tool over best-effort capture
    return 0


if __name__ == "__main__":
    sys.exit(main())
