#!/usr/bin/env python3
"""SessionStart hook: inject a compact harness status line (stdout -> context).

Budget: <= 6 lines. This is the entire per-session context cost of the
feedback system; everything else loads on demand.
"""
import datetime as dt
import json
import os
import subprocess
import sys

try:
    from harness_features import flag, active_overrides
except Exception:  # never let a config-reader import brick the banner
    def flag(key, default=None):
        return default

    def active_overrides():
        return {}

HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(HARNESS_ROOT, "state")


def _git(args, cwd):
    """Run a git command in `cwd`; stripped stdout or None on any failure
    (incl. a bad/missing cwd, which raises and is caught). Best-effort: a hook
    must never break a session over git."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd,
                           capture_output=True, text=True, timeout=3)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _branch_warning(session_cwd):
    """One banner line about the harness MAIN checkout's trunk state: a stranded-
    branch warning when the session sits on a non-main branch, OR a stale-trunk
    warning when it sits on main/master but local trunk is BEHIND origin (a
    remotely-merged PR that was never pulled rots local main and lets the next
    /retro re-propose already-merged work). Scoped via the SESSION's cwd (from the SessionStart payload),
    NOT this file's location — the active hook is always the trunk copy (wired by
    absolute path in settings), so keying off __file__ would report the trunk's
    branch no matter where the session actually is. Fires only when the git
    toplevel OF session_cwd IS the harness root: never in another project
    (different toplevel) and never in a `.claude/worktrees/*` checkout (toplevel is
    the worktree path, and its own `worktree-<name>` branch is correct there).
    High-signal because the harness learning flows (/retro, /harness-pr,
    /calibrate, /gc, /meta-retro) branch in-place and never `git checkout main`
    when done, silently stranding the NEXT session on a dead branch. Returns ''
    on a missing cwd or any git failure — the banner must still print."""
    if not session_cwd:
        return ""
    top = _git(["rev-parse", "--show-toplevel"], session_cwd)
    if not top:
        return ""
    if os.path.normcase(os.path.normpath(top)) != \
            os.path.normcase(os.path.normpath(HARNESS_ROOT)):
        return ""  # another repo, or a worktree checkout — non-main is fine there
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], session_cwd)
    if not branch or branch == "HEAD":
        return ""
    if branch in ("main", "master"):
        # On trunk: warn when local trunk is BEHIND origin (a PR merged on GitHub
        # and never pulled). A stale local main mis-reports topology and lets the
        # next /retro re-propose already-merged work (the 16-commit-drift incident).
        # Uses the LOCAL origin ref only -- a SessionStart hook does NOT hit the
        # network; returns '' when origin/<branch> is absent or already in sync.
        behind = _git(["rev-list", "--count", f"{branch}..origin/{branch}"], session_cwd)
        if not (behind and behind.isdigit() and int(behind) > 0):
            return ""
        ahead = _git(["rev-list", "--count", f"origin/{branch}..{branch}"], session_cwd)
        # ASCII only: the banner prints to a cp1252 console here, where a non-ASCII
        # glyph raises UnicodeEncodeError and crashes the hook (exit 1).
        if ahead and ahead.isdigit() and int(ahead) > 0:
            return (f"[harness] (!) local {branch} has DIVERGED from origin/{branch} "
                    f"({behind} behind, {ahead} ahead) - reconcile before branching")
        return (f"[harness] (!) local {branch} is {behind} commit(s) behind "
                f"origin/{branch} (a PR likely merged on GitHub) - "
                f"`git pull --ff-only` to refresh local trunk")
    # A non-main branch: stranded-branch warning (the in-place retro/PR flows
    # branch in place and may end the session without returning to trunk).
    try:
        merged = subprocess.run(
            ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
            cwd=session_cwd, capture_output=True, timeout=3).returncode == 0
    except Exception:
        merged = False
    note = "already merged - safe to" if merged else "not main -"
    # ASCII only: the banner prints to a cp1252 console here, where a non-ASCII
    # glyph raises UnicodeEncodeError and crashes the hook (exit 1).
    return (f"[harness] (!) on branch '{branch}' ({note} "
            f"`git checkout main` to return to trunk)")


def _jsonl(name):
    path = os.path.join(STATE, name)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def main() -> int:
    cwd = None
    try:
        data = json.load(sys.stdin)
        if isinstance(data, dict):
            cwd = data.get("cwd")
    except json.JSONDecodeError:
        pass
    preds = _jsonl("predictions.jsonl")
    scored = [p for p in preds if p.get("result") in ("hit", "miss")]
    pending = len(preds) - len(scored)
    if scored:
        hr = sum(1 for p in scored if p["result"] == "hit") / len(scored)
        calib = f"calibration {hr:.0%} on n={len(scored)}"
    else:
        calib = "calibration UNKNOWN (no scored predictions)"
    sessions = _jsonl("sessions.jsonl")
    since_meta = len(sessions)
    marker = os.path.join(STATE, "last_meta_retro")
    if os.path.exists(marker):
        try:
            with open(marker, encoding="utf-8") as f:
                last = dt.date.fromisoformat(f.read().strip())
            since_meta = sum(1 for s in sessions
                             if s.get("ts", "9999")[:10] > last.isoformat())
        except ValueError:
            pass
    # Quiet open-follow-up count (mirrors `harness followup count`: open AND within
    # the TTL). Shown only when >0 so a clean ledger stays silent. SOFT flag (ADR 0008):
    # same tunable decay window the harness CLI uses; default 30 if unset/garbage.
    try:
        _ttl_days = float(flag("workflow.followup_ttl_days", 30))
        if _ttl_days <= 0:
            _ttl_days = 30
    except (TypeError, ValueError):
        _ttl_days = 30
    fu_cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=_ttl_days)

    def _fu_open(r):
        if r.get("status") != "open":
            return False
        try:
            return dt.datetime.fromisoformat(r["ts"]) >= fu_cutoff
        except Exception:
            return True  # never silently drop an unparseable follow-up
    open_fu = sum(1 for r in _jsonl("followups.jsonl") if _fu_open(r))
    fu = f" | {open_fu} open follow-ups (/followups)" if open_fu else ""
    # SOFT flag (ADR 0008): banner verbosity. "off" suppresses the status summary;
    # the stranded-branch safety warning below is independent and always prints.
    banner = flag("observability.session_banner", "full")
    if banner == "minimal":
        print(f"[harness] {calib} | {pending} unscored predictions{fu}")
    elif banner != "off":
        print(f"[harness] {calib} | {pending} unscored predictions"
              f" | {since_meta} sessions since last /meta-retro"
              f" | learnings route to artifacts, not memory (routing-learnings skill)"
              f"{fu}")
    if banner != "off":
        # Extra surfacing (ADR 0008): one line whenever the local override file
        # diverges from defaults, so a flipped flag is never silently forgotten.
        ov = active_overrides()
        if ov:
            keys = ", ".join(sorted(ov)[:4])
            more = "" if len(ov) <= 4 else f" +{len(ov) - 4} more"
            print(f"[harness] features: {len(ov)} override(s) active "
                  f"({keys}{more}; `harness features`)")
    warn = _branch_warning(cwd)
    if warn:
        print(warn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
