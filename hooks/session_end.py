#!/usr/bin/env python3
"""SessionEnd hook: append one summary record per session, reap the fleet log, clean gate flags.

The fleet-log reap (Mission Control P4): fleet.eventlog.compact() is the wired lifecycle trigger its
docstring already names ("the harness wires it into session-end"). Correctness never depends on it
(every read is reap-aware), so this is space reclamation and is fail-open — the reaper must never
brick session end. (followups d72eec / ed2b67; deferred out of Agent Mail PR #121.)
"""
import datetime as dt
import json
import os
import sys

try:
    from harness_features import flag
except Exception:
    def flag(key, default=None):
        return default

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HARNESS_ROOT)
import private_state
STATE = os.path.join(HARNESS_ROOT, "state")


def _count(name, session):
    path = os.path.join(STATE, name)
    return sum(1 for record in private_state.read_jsonl(path)
               if record.get("session") == session)


def _reap_fleet():
    """Best-effort fleet-log compaction (Mission Control P4). Fail-open: never brick session end."""
    try:
        sys.path.insert(0, HARNESS_ROOT)
        from fleet import eventlog as el
        el.compact(STATE)
    except Exception:
        pass


def _scrub_private_state():
    """Best-effort raw-excerpt expiry. Privacy housekeeping must never brick session end."""
    if not flag("privacy.scrub_on_session_end", True):
        return
    try:
        from privacy_state import DEFAULT_RETENTION_DAYS, scrub_raw_excerpts
        days = {
            "corrections.jsonl": flag(
                "privacy.correction_excerpt_retention_days", DEFAULT_RETENTION_DAYS),
            "candidates.jsonl": flag(
                "privacy.failure_excerpt_retention_days", DEFAULT_RETENTION_DAYS),
        }
        scrub_raw_excerpts(STATE, retention_days=days, apply=True)
    except Exception:
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    session = data.get("session_id", "?")
    private_state.append_jsonl(os.path.join(STATE, "sessions.jsonl"), {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "session": session,
        "corrections": _count("corrections.jsonl", session),
        "predictions": _count("predictions.jsonl", session),
        "skills_fired": _count("skill_usage.jsonl", session),
    })
    # reap the fleet event log at this low-contention moment (space reclamation, fail-open)
    _reap_fleet()
    _scrub_private_state()
    # clean up both per-session retro-nudge flags (stop_retro_gate + stop_cadence_gate)
    session_file_id = private_state.safe_filename_id(session, "session")
    for name in (f"retro_gate_{session_file_id}", f"cadence_gate_{session_file_id}"):
        try:
            os.remove(os.path.join(STATE, name))
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
