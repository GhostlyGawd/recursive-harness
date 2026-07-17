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
        # Behind, NOT diverged: ACT instead of suggest, but SAFELY. Gate on a CLEAN
        # tracked tree first -- auto-advancing a dirty tree is unsafe (could surprise
        # an in-progress edit). `status --porcelain --untracked-files=no` is exactly ""
        # only when no tracked change is staged or unstaged; any error -> None -> warn.
        warn = (f"[harness] (!) local {branch} is {behind} commit(s) behind "
                f"origin/{branch} (a PR likely merged on GitHub) - "
                f"`git pull --ff-only` to refresh local trunk")
        status = _git(["status", "--porcelain", "--untracked-files=no"], session_cwd)
        if status != "":
            return warn  # dirty tracked tree (or git error -> None) -> fail safe to advisory
        # Clean tree: NETWORK-FREE fast-forward of local trunk to the ALREADY-FETCHED
        # origin ref. NOT `git pull` (that hits the network and can block/fail a session
        # start -- a SessionStart hook must never touch the network). `merge --ff-only`
        # advances local main from what was already fetched, no network.
        if _git(["merge", "--ff-only", f"origin/{branch}"], session_cwd) is not None:
            return (f"[harness] refreshed local {branch}: fast-forwarded {behind} commit(s) to "
                    f"origin/{branch} (was behind a merged PR)")
        return warn  # not actually fast-forwardable -> fail safe to advisory
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


def _heal_counts(cwd):
    """(escalate_count, stuck_count) for the SESSION's repo via heal.py's single-sourced
    predicates - do NOT re-implement the failure math here. Imports heal.py by path and
    keys off the payload `cwd` (NOT os.getcwd()/__file__: the active hook is always the
    trunk copy, so keying off this file would read the wrong repo). Fail-open: (0, 0)."""
    try:
        import importlib.util
        heal_py = os.path.join(HARNESS_ROOT, "skills", "auto-healer", "heal.py")
        spec = importlib.util.spec_from_file_location("_heal_banner", heal_py)
        heal = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(heal)
        repo = heal._repo_key(root=cwd or os.getcwd())
        bp, ap = heal._paths(repo)
        m = heal._metrics(heal._read(bp), heal._read(ap))
        return int(m.get("escalate_count", 0)), int(m.get("stuck_count", 0))
    except Exception:
        return 0, 0


def main() -> int:
    # cp1252-safe stdout/stderr: degrade non-ASCII to '?' instead of crashing mid-print
    # (proposal P-2026-017).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
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
    # Plain outcome language (2026-07-05, session 975732da, product-UX roadmap item 1:
    # the user-model "explain it like a video game" rule, evidence 5).
    if scored:
        hr = sum(1 for p in scored if p["result"] == "hit") / len(scored)
        calib = f"right {hr:.0%} of the last {len(scored)} predictions"
    else:
        calib = "no predictions checked yet"
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
    # NOTE (2026-06-28): the open-follow-up COUNT was removed from this banner.
    # Follow-ups are pull-only (`/followups`) by the user's "surface only on pull,
    # never push" rule -- a count recited every SessionStart was itself the push that
    # rule forbids, and read as an ever-climbing junk pile. The ledger audited HEALTHY
    # (91% closed, nothing stale > ~10d, median time-to-close 0d), so a per-session
    # count bought no benefit it didn't already get from `/followups`. Deliberately NOT
    # replaced with a delta/staleness alarm: that is still a push and new accretion,
    # against the user's reduce-net-weight stance; revisit only if items start to rot.
    # SOFT flag (ADR 0008): banner verbosity. "off" suppresses the status summary;
    # the stranded-branch safety warning below is independent and always prints.
    banner = flag("observability.session_banner", "full")
    if banner == "minimal":
        print(f"[harness] {calib} | {pending} awaiting a score")
    elif banner != "off":
        print(f"[harness] {calib} | {pending} awaiting a score"
              f" | {since_meta} sessions since the last monthly self-review (/meta-retro)"
              f" | lessons become repo changes, not memory"
              f" | `harness explain <term>` defines anything here")
    if banner != "off":
        # Extra surfacing (ADR 0008): one line whenever the local override file
        # diverges from defaults, so a flipped flag is never silently forgotten.
        ov = active_overrides()
        if ov:
            keys = ", ".join(sorted(ov)[:4])
            more = "" if len(ov) <= 4 else f" +{len(ov) - 4} more"
            print(f"[harness] features: {len(ov)} override(s) active "
                  f"({keys}{more}; `harness features`)")
        # Heal-count line (ADR 0008 SOFT flag observability.heal_banner, default false ->
        # ships dark): JIT-surface a repo's unresolved root defects at session start, the
        # highest-leverage moment. Pull-only (`/heal`), never the web; fail-open to 0.
        if flag("observability.heal_banner", False):
            esc, stuck = _heal_counts(cwd)
            if esc or stuck:
                print(f"[harness] heal: {esc} escalate / {stuck} stuck (/heal)")
        # Autonomy graduation progress (roadmap item 10, session 975732da): the
        # 20-proposal bar only motivates if it is visible between /meta-retros.
        # Full banner only; fail-open — a bad autonomy.json must not cost the session.
        if banner == "full":
            try:
                with open(os.path.join(HARNESS_ROOT, "autonomy.json"), encoding="utf-8") as f:
                    cats = json.load(f).get("categories", {})
                parts = [f"{k} {v.get('proposed', 0)}/20" for k, v in cats.items()
                         if v.get("graduable") and not v.get("auto_merge")]
                if parts:
                    print(f"[harness] trust toward auto-merge: {' - '.join(parts)} "
                          f"(reviewed at /meta-retro)")
            except (OSError, ValueError, AttributeError):
                pass
    warn = _branch_warning(cwd)
    if warn:
        print(warn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
