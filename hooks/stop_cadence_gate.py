#!/usr/bin/env python3
"""Stop hook: the MULTI-SESSION retro cadence gate.

stop_retro_gate.py only fires inside a single session that hit >= 3 corrections.
Across many low-correction sessions, /retro can go unrun for a long stretch
(observed: 6 sessions with no retro — cross-Grove retro, PR #22), because that
gate is per-session + correction-keyed. This gate is the complement: nudge /retro
once when >= N distinct sessions have started since the last retro landed,
regardless of per-session corrections. (followup 2e87fe)

Fail-open everywhere: a Stop hook must never brick a session, and a MISSED nudge
is harmless while a SPURIOUS one is annoying — so any uncertainty => no nudge.
"""
import datetime as dt
import json
import os
import subprocess
import sys

try:
    from harness_features import flag, num
except Exception:  # never let a config-reader import brick the hook
    def flag(key, default=None):
        return default

    def num(key, default):
        return float(default)

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HARNESS_ROOT)
import private_state
STATE = os.path.join(HARNESS_ROOT, "state")
SESSIONS_SINCE_RETRO_THRESHOLD = 5


def _last_retro_epoch():
    """Commit time (epoch int) of the most recent retro-related commit.

    None on git error -> caller fails open (no nudge). 0 if git ran cleanly but
    found no retro commit at all -> retro is overdue, count every session.
    """
    try:
        # Anchor to the conventional-commit prefix (`^retro(`/`retro:`/`retro/`). An
        # UNanchored `retro[(:/ ]` matched any commit whose message merely contained
        # "retro " -- including THIS hook's own "...retro cadence gate..." commit --
        # resetting the clock so the gate would silently never fire (auditor catch).
        # The real `retro(...)` commit lands in history via its merge, so the
        # anchored grep still finds the last retro.
        r = subprocess.run(
            ["git", "-C", HARNESS_ROOT, "log", "-1", "--format=%ct",
             "--extended-regexp", "--grep=^retro[(:/]"],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    if not out:
        return 0
    return int(out) if out.isdigit() else None


def _sessions_since(epoch) -> int:
    """Count distinct sessions in sessions.jsonl that started after `epoch`."""
    log = os.path.join(STATE, "sessions.jsonl")
    seen = set()
    try:
        for rec in private_state.read_jsonl(log):
            sid, ts = rec.get("session"), rec.get("ts")
            if not sid or not ts:
                continue
            try:
                rec_epoch = dt.datetime.fromisoformat(ts).timestamp()
            except (ValueError, TypeError):
                continue
            if rec_epoch > epoch:
                seen.add(sid)
    except OSError:
        return 0
    return len(seen)


def main() -> int:
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal 2026-06-23-utf8-stdout-all-entrypoints).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    # SOFT flag (ADR 0008): disable the multi-session retro cadence nudge.
    if not flag("nudges.cadence_gate", True):
        return 0
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # fail open on malformed input; never brick the session
    if data.get("stop_hook_active"):
        return 0
    session = data.get("session_id", "?")
    # Don't double-nudge: if the per-session correction gate already fired, skip.
    if os.path.exists(os.path.join(STATE, f"retro_gate_{session}")):
        return 0
    gate_flag = os.path.join(STATE, f"cadence_gate_{session}")  # not `flag`: that name is the feature reader
    if os.path.exists(gate_flag):
        return 0
    ref = _last_retro_epoch()
    if ref is None:
        return 0  # can't determine the last retro -> fail open (no nudge)
    n = _sessions_since(ref)
    # SOFT flag (ADR 0008): how many sessions without a retro before the nudge fires.
    threshold = int(num("nudges.retro_cadence_sessions", SESSIONS_SINCE_RETRO_THRESHOLD))
    if n >= threshold:
        try:
            private_state.atomic_write_text(gate_flag, "nudged\n")
        except OSError:
            return 0  # if we cannot record the once-per-session flag, do not nudge
        print(json.dumps({
            "decision": "block",
            "reason": (f"Cadence gate: {n} sessions since the last retro landed and none "
                       "has run. Run /retro to mine the accumulated cross-session signal "
                       "into harness diffs with provenance. (Fires once per session.)"),
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
