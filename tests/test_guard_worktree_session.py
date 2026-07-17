#!/usr/bin/env python3
"""Tests for guard_worktree_session.py (Guard B) — authored BEFORE the hook.

Guard B = "one live session per TREE", with OWNERSHIP THAT FOLLOWS THE SESSION'S
CWD — the stateful complement to Guard A (guard_worktree_isolation.py). Guard A
stops a session reaching INTO a sibling worktree's files; Guard B stops a SECOND
live session colliding INSIDE the same tree (a worktree OR the main checkout).
Scope decision (user, 2026-06-17): EVERY tree is guarded. On collision: BLOCK,
and make the block an ONBOARDING step that walks the user into their own worktree.

Contract under test (hooks/guard_worktree_session.py, a PreToolUse + SessionEnd +
SessionStart hook):

  Input JSON: {hook_event_name, tool_name, tool_input, cwd, session_id, source}

  TREE := the worktree root if cwd is inside `.claude/worktrees/<name>`, else the
  nearest ancestor of cwd with a `.git` entry (repo root), else cwd. Keys are
  os.path.normcase'd.

  A single per-REPO map `<repo>/state/session_owners.json` == {tree_key:{session_id,
  ts,...}} holds owners for the checkout AND all its `.claude/worktrees/*` (a
  worktree resolves repo root by stripping `.claude/worktrees/<name>`).

  PreToolUse: a DIFFERENT, FRESH owner of my tree -> BLOCK (exit 2, stderr has
  BLOCKED+worktree). Else CLAIM my tree AND drop any OTHER tree I owned (I moved —
  ownership follows cwd, so EnterWorktree frees the tree I left). A stale owner
  (heartbeat older than TTL) or a non-finite heartbeat is takeover-able.
  SessionEnd: release every tree this session owns. SessionStart source!="startup"
  (resume/clear/compact): release the cwd-resolved tree (handles /clear minting a
  new session_id). Escape hatch HARNESS_ALLOW_MULTI_SESSION in {1,true,yes,on}.
  Fails OPEN (exit 0) on malformed/pathological input, missing session_id, or any
  error — and NEVER exits anything other than 0 or 2.

Block-cases assert 'BLOCKED'+'worktree' in stderr so a MISSING hook (exit 2 with a
'No such file' error) cannot masquerade as a real block — keeps red honest.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The REAL hook (its HARNESS_ROOT == this repo). Used as a FALLBACK for payloads with
# no resolvable repo copy -- garbage / no-cwd (fail open before the scope check) and a
# FOREIGN repo with no copy (which exercises the real Fix-B scope no-op). Synthetic
# repos from new_main_tree() install their OWN copy so the hook's HARNESS_ROOT == that
# repo and Fix B's `repo == HARNESS_ROOT` check passes there. Without that, every
# fixture's tempdir cwd would be != the real HARNESS_ROOT and the whole suite would
# silently no-op (auditor F2, 2026-06-18).
_HOOK_SRC = os.environ.get(
    "GUARD_B_HOOK", os.path.join(ROOT, "hooks", "guard_worktree_session.py")
)
MAP_REL = os.path.join("state", "session_owners.json")
_WT_RE = re.compile(
    r"^(.*?[\\/]\.claude[\\/]worktrees[\\/][^\\/]+)(?:[\\/].*)?$", re.IGNORECASE)
FAILURES = []
_TMPDIRS = []


def run(payload, env_extra=None):
    env = dict(os.environ)
    env.pop("HARNESS_ALLOW_MULTI_SESSION", None)
    if env_extra:
        env.update(env_extra)
    # Invoke the hook copy installed in the payload's OWN repo (so HARNESS_ROOT matches
    # and Fix B's scope check passes). Fall back to the real hook when the cwd has no
    # resolvable repo copy: garbage/no-cwd payloads (which fail open before the scope
    # check) and FOREIGN repos with no copy (exactly the Fix-B no-op under test).
    hook = _HOOK_SRC
    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    if isinstance(cwd, str) and cwd.strip():
        repo = _repo_root_for(cwd)
        cand = os.path.join(repo, "hooks", "guard_worktree_session.py") if repo else ""
        if cand and os.path.exists(cand):
            hook = cand
    p = subprocess.run([sys.executable, hook], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def pl(tool_input, cwd, session="s1", event="PreToolUse", tool="Read", source=None,
       transcript=None):
    p = {"hook_event_name": event, "tool_name": tool,
         "tool_input": tool_input, "cwd": cwd, "session_id": session}
    if source is not None:
        p["source"] = source
    if transcript is not None:
        p["transcript_path"] = transcript
    return p


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def blocked(rc, err):
    low = err.lower()
    return rc == 2 and "blocked" in low and "worktree" in low


def warned(rc, out):
    """A NON-BLOCKING warning: exit 0 + stdout JSON whose systemMessage onboards to
    a worktree (a PreToolUse hook's stderr is ignored on exit 0)."""
    if rc != 0 or not out.strip():
        return False
    try:
        j = json.loads(out)
    except ValueError:
        return False
    msg = (j.get("systemMessage") or "").lower()
    return ("worktree" in msg) and ("another session" in msg)


def silent(rc, out):
    """Allowed with NO warning: exit 0 and no systemMessage on stdout."""
    if rc != 0:
        return False
    if not out.strip():
        return True
    try:
        return not json.loads(out).get("systemMessage")
    except ValueError:
        return True


def _strip_extended(path):
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[len("\\\\?\\UNC\\"):]
    if path.startswith("\\\\?\\"):
        return path[len("\\\\?\\"):]
    return path


def _key(tree):
    # Mirror the hook's _normalize exactly (strip \\?\ -> abspath -> normpath ->
    # normcase; NO realpath) so map keys match.
    p = _strip_extended(os.path.expanduser(tree))
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))


def _norm(p):
    r"""Normalize a path for filesystem lookup of an installed hook copy (strip \\?\,
    expanduser, abspath, normpath; NO normcase -- we only need a real path)."""
    return os.path.normpath(os.path.abspath(_strip_extended(os.path.expanduser(p))))


def _repo_root_for(cwd):
    """Mirror the hook's repo resolution so run() can find which installed copy to
    invoke: a `.claude/worktrees/<name>` cwd strips to the main checkout; else the
    nearest ancestor with a `.git` entry; else the normalized cwd."""
    norm = _norm(cwd)
    m = _WT_RE.match(norm)
    if m:
        return os.path.dirname(os.path.dirname(os.path.dirname(m.group(1))))
    d = norm
    for _ in range(80):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return norm


def new_main_tree():
    """Fake main checkout that doubles as its OWN HARNESS_ROOT: a temp dir with a `.git`
    DIRECTORY and an installed byte-identical copy of Guard B at `<d>/hooks/`. The copy
    computes HARNESS_ROOT == d, so Fix B's `repo == HARNESS_ROOT` scope check passes for
    cwds inside d and its worktrees -- exercising the real guard logic in a sandbox
    instead of silently no-opping."""
    d = tempfile.mkdtemp(prefix="guardb_main_")
    _TMPDIRS.append(d)
    os.mkdir(os.path.join(d, ".git"))
    os.makedirs(os.path.join(d, "hooks"), exist_ok=True)
    shutil.copyfile(_HOOK_SRC, os.path.join(d, "hooks", "guard_worktree_session.py"))
    # Guard B hard-imports its sibling _wtpaths (shared worktree-path helpers, 3939d8),
    # so the isolated copy needs it alongside or the subprocess dies on ImportError.
    shutil.copyfile(
        os.path.join(os.path.dirname(_HOOK_SRC), "_wtpaths.py"),
        os.path.join(d, "hooks", "_wtpaths.py"),
    )
    # State writes are centralized in the root-level stdlib primitive; preserve the
    # synthetic repo's production layout so the copied guard exercises that dependency.
    shutil.copyfile(os.path.join(ROOT, "private_state.py"),
                    os.path.join(d, "private_state.py"))
    return d


def new_worktree(repo, name="wt-a"):
    """Fake linked worktree `<repo>/.claude/worktrees/<name>` holding a `.git` FILE."""
    wt = os.path.join(repo, ".claude", "worktrees", name)
    os.makedirs(wt, exist_ok=True)
    with open(os.path.join(wt, ".git"), "w") as f:
        f.write("gitdir: /dev/null\n")
    return wt


def make_transcript(bucket, name, age_seconds):
    """Create a fake session transcript <bucket>/<name> with mtime = now-age."""
    os.makedirs(bucket, exist_ok=True)
    path = os.path.join(bucket, name)
    with open(path, "w") as f:
        f.write("{}\n")
    t = time.time() - age_seconds
    os.utime(path, (t, t))
    return path


def bucket_with(specs):
    """Fresh temp transcript-bucket dir holding transcripts: specs is a list of
    (filename, age_seconds). Mirrors a `projects/<cwd-key>/` dir. Returns its path."""
    b = tempfile.mkdtemp(prefix="guardb_bkt_")
    _TMPDIRS.append(b)
    for name, age in specs:
        make_transcript(b, name, age)
    return b


def read_map(repo):
    try:
        with open(os.path.join(repo, MAP_REL)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def owner_of(tree, repo=None):
    """The owner entry for `tree` in `repo`'s map (repo defaults to tree, the
    main-checkout case). None if unowned."""
    return read_map(repo if repo is not None else tree).get(_key(tree))


def set_ts(tree, ts, repo=None, sid="OTHER"):
    """Write a raw owner entry with a chosen ts (to simulate staleness / corrupt
    heartbeats deterministically). Writes the map the hook would read."""
    repo = repo if repo is not None else tree
    m = read_map(repo)
    m[_key(tree)] = {"session_id": sid, "ts": ts}
    os.makedirs(os.path.join(repo, "state"), exist_ok=True)
    with open(os.path.join(repo, MAP_REL), "w") as f:
        json.dump(m, f)


def backdate(tree, seconds, repo=None):
    repo = repo if repo is not None else tree
    o = owner_of(tree, repo)
    if o is None:
        check("backdate precondition: an owner exists to age", False, "no owner")
        return False
    set_ts(tree, time.time() - seconds, repo=repo, sid=o["session_id"])
    return True


# =====================================================================
# 1. Core: second live session in the SAME tree is blocked; owner re-entrant
# =====================================================================
repo = new_main_tree()
wt = new_worktree(repo, "wt-a")

rc, _, _ = run(pl({"file_path": os.path.join(wt, "x.py")}, wt, session="A"))
check("worktree: first session A allowed (claims)", rc == 0, f"rc={rc}")
check("worktree: registry (in repo map) records owner A",
      (owner_of(wt, repo) or {}).get("session_id") == "A", read_map(repo))

rc, _, err = run(pl({"file_path": os.path.join(wt, "x.py")}, wt, session="B"))
check("worktree: second live session B blocked", blocked(rc, err), f"rc={rc} err={err[:80]}")

rc, _, _ = run(pl({"file_path": os.path.join(wt, "x.py")}, wt, session="A"))
check("worktree: owner A re-entrant (still allowed)", rc == 0, f"rc={rc}")
check("worktree: blocked B did NOT steal ownership",
      (owner_of(wt, repo) or {}).get("session_id") == "A", read_map(repo))

# =====================================================================
# 2. Scope: the OWNER MAP never blocks the MAIN checkout (session_id churn would
#    false-block a single session's own successor — see section 14 for how main
#    concurrency is actually caught, via transcript liveness). A payload with NO
#    transcript_path therefore never blocks the main checkout here. The main tree
#    is still CLAIMED for tracking. (owner-map churn fix 2026-06-17)
# =====================================================================
repo2 = new_main_tree()
rc, _, _ = run(pl({"file_path": os.path.join(repo2, "f.py")}, repo2, session="A"))
check("main checkout: first session A allowed", rc == 0, f"rc={rc}")

rc, _, err = run(pl({"file_path": os.path.join(repo2, "f.py")}, repo2, session="B"))
check("main checkout: 2nd session NOT blocked via owner map (no transcript provided)",
      rc == 0, f"rc={rc} err={err[:80]}")
check("main checkout: B becomes owner (still claimed for tracking)",
      (owner_of(repo2) or {}).get("session_id") == "B", read_map(repo2))

# =====================================================================
# 3. Different trees never cross-block; one shared per-repo map holds them all
# =====================================================================
wt_b = new_worktree(repo, "wt-b")
rc, _, _ = run(pl({"file_path": os.path.join(wt_b, "y.py")}, wt_b, session="D"))
check("sibling worktree wt-b: independent session allowed (no cross-block)", rc == 0, f"rc={rc}")
rc, _, _ = run(pl({"file_path": os.path.join(repo, "z.py")}, repo, session="E"))
check("repo root containing worktrees is its own tree (allowed)", rc == 0, f"rc={rc}")
m = read_map(repo)
check("one shared repo map holds wt-a, wt-b, and the checkout as distinct keys",
      len(m) == 3 and {v["session_id"] for v in m.values()} == {"A", "D", "E"}, m)

# =====================================================================
# 4. Staleness TTL: a stale (crashed/idle-beyond-TTL) owner can be taken over
# =====================================================================
repo3 = new_main_tree(); wt3 = new_worktree(repo3, "wt")  # blocking is worktree-scoped now
rc, _, _ = run(pl({"file_path": os.path.join(wt3, "a")}, wt3, session="OLD"))
check("ttl: OLD claims tree", rc == 0, f"rc={rc}")
backdate(wt3, 10 * 24 * 3600, repo=repo3)
rc, _, _ = run(pl({"file_path": os.path.join(wt3, "a")}, wt3, session="NEW"))
check("ttl: stale owner taken over by NEW (allowed)", rc == 0, f"rc={rc}")
check("ttl: NEW is now the owner", (owner_of(wt3, repo3) or {}).get("session_id") == "NEW", read_map(repo3))
rc, _, err = run(pl({"file_path": os.path.join(wt3, "a")}, wt3, session="LATE"))
check("ttl: fresh owner still blocks newcomer", blocked(rc, err), f"rc={rc}")

# =====================================================================
# 5. SessionEnd release: clean exit frees the tree immediately
# =====================================================================
repo4 = new_main_tree()
rc, _, _ = run(pl({"file_path": os.path.join(repo4, "a")}, repo4, session="OWN"))
check("release: OWN claims tree", rc == 0, f"rc={rc}")
rc, _, _ = run(pl({}, repo4, session="STRANGER", event="SessionEnd", tool=""))
check("release: non-owner SessionEnd does not release (exit 0)", rc == 0, f"rc={rc}")
check("release: claim survives non-owner SessionEnd",
      (owner_of(repo4) or {}).get("session_id") == "OWN", read_map(repo4))
rc, _, _ = run(pl({}, repo4, session="OWN", event="SessionEnd", tool=""))
check("release: owner SessionEnd exits 0", rc == 0, f"rc={rc}")
check("release: owner SessionEnd cleared the claim", owner_of(repo4) is None, read_map(repo4))
rc, _, _ = run(pl({"file_path": os.path.join(repo4, "a")}, repo4, session="NEXT"))
check("release: tree free after owner exit -> NEXT allowed", rc == 0, f"rc={rc}")

# =====================================================================
# 6. Escape hatch (value-gated)
# =====================================================================
repo5 = new_main_tree(); wt5 = new_worktree(repo5, "wt")  # blocking is worktree-scoped
run(pl({"file_path": os.path.join(wt5, "a")}, wt5, session="HOLD"))
for val in ("1", "true", "YES", "on"):
    rc, _, _ = run(pl({"file_path": os.path.join(wt5, "a")}, wt5, session="X"),
                   env_extra={"HARNESS_ALLOW_MULTI_SESSION": val})
    check(f"hatch ={val!r} enables bypass", rc == 0, f"rc={rc}")
for val in ("0", "false", "no", "off", ""):
    rc, _, err = run(pl({"file_path": os.path.join(wt5, "a")}, wt5, session="X"),
                     env_extra={"HARNESS_ALLOW_MULTI_SESSION": val})
    check(f"hatch ={val!r} does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")
# Regression (harness-auditor 2026-06-17): the TTL must NOT be env-overridable —
# a tiny HARNESS_SESSION_TTL_SECONDS would be a self-assertable bypass (instantly
# stale-out + evict the live owner). It must be ignored entirely; the 2nd session
# still blocks regardless of the value.
for val in ("0", "0.0001", "1", "-5", "99999999"):
    rc, _, err = run(pl({"file_path": os.path.join(wt5, "a")}, wt5, session="ATK"),
                     env_extra={"HARNESS_SESSION_TTL_SECONDS": val})
    check(f"TTL env override ={val!r} is NOT honored (no self-assertable bypass)",
          blocked(rc, err), f"rc={rc}")

# =====================================================================
# 7. Tool-agnostic block + onboarding message content
# =====================================================================
repo6 = new_main_tree(); wt6 = new_worktree(repo6, "wt")  # blocking is worktree-scoped
run(pl({"file_path": os.path.join(wt6, "a")}, wt6, session="OWN"))
for tool, ti in (("Edit", {"file_path": os.path.join(wt6, "a")}),
                 ("Write", {"file_path": os.path.join(wt6, "a")}),
                 ("Bash", {"command": "ls"}),
                 ("Grep", {"pattern": "x", "path": wt6}),
                 ("Glob", {"pattern": "**/*", "path": wt6})):
    rc, _, err = run(pl(ti, wt6, session="B", tool=tool))
    check(f"second session blocked on {tool}", blocked(rc, err), f"rc={rc}")
rc, _, _ = run(pl({"command": "ls"}, wt6, session="OWN", tool="Bash"))
check("owner allowed on Bash (heartbeat)", rc == 0, f"rc={rc}")
_, _, err = run(pl({"file_path": os.path.join(wt6, "a")}, wt6, session="B"))
low = err.lower()
check("onboarding message mentions starting a worktree",
      ("--worktree" in low) or ("enterworktree" in low), err[:140])
check("onboarding message names the escape hatch",
      "harness_allow_multi_session" in low, err[:140])

# =====================================================================
# 8. EnterWorktree (HIGH red-team fix): ownership follows cwd — moving into a
#    worktree RELEASES the orphaned main-checkout claim, so a genuine new
#    terminal in main is NOT false-blocked.
# =====================================================================
repo_ew = new_main_tree()
wt_ew = new_worktree(repo_ew, "feat")
rc, _, _ = run(pl({"file_path": os.path.join(repo_ew, "a")}, repo_ew, session="A"))
check("EnterWorktree: A claims main checkout", (owner_of(repo_ew) or {}).get("session_id") == "A", read_map(repo_ew))
# A runs EnterWorktree: its subsequent tool calls have cwd inside the worktree.
rc, _, _ = run(pl({"file_path": os.path.join(wt_ew, "b")}, wt_ew, session="A"))
check("EnterWorktree: A (same sid) now works in the worktree (allowed)", rc == 0, f"rc={rc}")
check("EnterWorktree: A's worktree claim recorded", (owner_of(wt_ew, repo_ew) or {}).get("session_id") == "A", read_map(repo_ew))
check("EnterWorktree: A's old main-checkout claim was RELEASED (no orphan)",
      owner_of(repo_ew) is None, read_map(repo_ew))
rc, _, _ = run(pl({"file_path": os.path.join(repo_ew, "c")}, repo_ew, session="B"))
check("EnterWorktree: genuine new terminal B in main is NOT false-blocked", rc == 0, f"rc={rc}")
# And A's clean SessionEnd (cwd=worktree) frees the worktree claim it still holds.
run(pl({}, wt_ew, session="A", event="SessionEnd", tool=""))
check("EnterWorktree: A SessionEnd frees its worktree claim", owner_of(wt_ew, repo_ew) is None, read_map(repo_ew))

# =====================================================================
# 9. SessionStart(resume|clear) releases the cwd tree so a user is NOT blocked
#    by their OWN just-cleared claim; startup (new terminal) does NOT release.
# =====================================================================
for src in ("clear", "resume", "compact"):
    repo_c = new_main_tree()
    run(pl({"file_path": os.path.join(repo_c, "a")}, repo_c, session="OLD"))
    rc, _, _ = run(pl({}, repo_c, session="NEWID", event="SessionStart", tool="", source=src))
    check(f"SessionStart source={src} exits 0", rc == 0, f"rc={rc}")
    check(f"SessionStart source={src} released the stale-by-transition claim",
          owner_of(repo_c) is None, read_map(repo_c))
    rc, _, _ = run(pl({"file_path": os.path.join(repo_c, "a")}, repo_c, session="NEWID"))
    check(f"after source={src}, new session claims freely (no false-block)", rc == 0, f"rc={rc}")

repo_s = new_main_tree(); wt_s = new_worktree(repo_s, "wt")  # blocking is worktree-scoped
run(pl({"file_path": os.path.join(wt_s, "a")}, wt_s, session="LIVE"))
rc, _, _ = run(pl({}, wt_s, session="OTHER", event="SessionStart", tool="", source="startup"))
check("SessionStart source=startup does NOT release", rc == 0, f"rc={rc}")
check("SessionStart startup left the live owner intact",
      (owner_of(wt_s, repo_s) or {}).get("session_id") == "LIVE", read_map(repo_s))
rc, _, err = run(pl({"file_path": os.path.join(wt_s, "a")}, wt_s, session="OTHER"))
check("new terminal (startup) still blocked by live owner", blocked(rc, err), f"rc={rc}")

# =====================================================================
# 10. Non-finite / corrupt heartbeat (red-team): inf/-inf/NaN/'inf' must be
#     treated as STALE -> takeover ALLOWED, never crash _block, never a fail-open
#     two-owner bypass, never a false BLOCK. (Hook only writes finite time.time();
#     this models an externally corrupted shared map.)
# =====================================================================
for bad in (float("inf"), float("-inf"), float("nan"), "inf", "-inf", "nan",
            "oops", None, 10 ** 400):  # 10**400 overflows float() -> must be stale
    repo_n = new_main_tree()
    set_ts(repo_n, bad, sid="GHOST")  # a "fresh" but non-finite/garbage owner
    rc, _, err = run(pl({"file_path": os.path.join(repo_n, "a")}, repo_n, session="REAL"))
    check(f"corrupt ts={bad!r}: newcomer ALLOWED (treated stale), no crash",
          rc == 0, f"rc={rc} err={err[:60]}")
    check(f"corrupt ts={bad!r}: newcomer becomes sole owner (one-owner invariant)",
          (owner_of(repo_n) or {}).get("session_id") == "REAL", read_map(repo_n))

# A NaN-ts written via real JSON tokens (Infinity/NaN are valid to python's json):
repo_j = new_main_tree()
os.makedirs(os.path.join(repo_j, "state"), exist_ok=True)
with open(os.path.join(repo_j, MAP_REL), "w") as f:
    f.write('{"%s": {"session_id": "GHOST", "ts": Infinity}}' % _key(repo_j).replace("\\", "\\\\"))
rc, _, _ = run(pl({"file_path": os.path.join(repo_j, "a")}, repo_j, session="REAL"))
check("corrupt ts=Infinity (raw json token): newcomer allowed, no exit-1 crash", rc == 0, f"rc={rc}")

# =====================================================================
# 11. Fail OPEN: malformed / pathological / missing-id must NEVER brick (never
#     exit anything but 0/2). Includes deeply-nested JSON -> RecursionError.
# =====================================================================
p = subprocess.run([sys.executable, _HOOK_SRC], input="not json{{", capture_output=True, text=True)
check("fails open on garbage stdin", p.returncode == 0, f"rc={p.returncode}")

deep = "[" * 6000 + "]" * 6000  # RecursionError in json.load — must still exit 0
p = subprocess.run([sys.executable, _HOOK_SRC], input=deep, capture_output=True, text=True)
check("deeply-nested JSON fails OPEN (exit 0, not 1)", p.returncode == 0, f"rc={p.returncode} err={p.stderr[:60]}")

deep_payload = '{"session_id":"A","cwd":"/x","hook_event_name":"PreToolUse","tool_input":' + "[" * 6000 + "]" * 6000 + "}"
p = subprocess.run([sys.executable, _HOOK_SRC], input=deep_payload, capture_output=True, text=True)
check("deeply-nested value inside a real payload fails OPEN (exit 0)", p.returncode == 0, f"rc={p.returncode}")

repo7 = new_main_tree()
payload = {"hook_event_name": "PreToolUse", "tool_name": "Read",
           "tool_input": {"file_path": os.path.join(repo7, "a")}, "cwd": repo7}
rc, _, _ = run(payload)
check("missing session_id fails open (allowed)", rc == 0, f"rc={rc}")
check("missing session_id did NOT write any owner", owner_of(repo7) is None, read_map(repo7))

rc, _, _ = run(pl({"file_path": os.path.join(repo7, "a")}, repo7, session=""))
check("blank session_id fails open (allowed)", rc == 0, f"rc={rc}")

p = subprocess.run([sys.executable, _HOOK_SRC], input='["a","b"]', capture_output=True, text=True)
check("non-dict json fails open", p.returncode == 0, f"rc={p.returncode}")
rc, _, _ = run({"hook_event_name": "PreToolUse", "tool_name": "Read",
                "tool_input": "oops", "cwd": repo7, "session_id": "Z"})
check("non-dict tool_input fails open", rc == 0, f"rc={rc}")

# Non-string session_id / cwd fail open.
for bad in (123, None, ["x"], {"a": 1}):
    rc, _, _ = run({"hook_event_name": "PreToolUse", "tool_name": "Read",
                    "tool_input": {}, "cwd": repo7, "session_id": bad})
    check(f"non-string session_id {bad!r} fails open", rc == 0, f"rc={rc}")
rc, _, _ = run({"hook_event_name": "PreToolUse", "tool_name": "WebFetch",
                "tool_input": {"url": "https://example.com"}, "session_id": "Z"})
check("absent cwd fails open (allowed)", rc == 0, f"rc={rc}")

# =====================================================================
# 12. No orphan temp files left in state/ after many sequential writes (Windows
#     os.replace retry + temp cleanup).
# =====================================================================
repo_t = new_main_tree()
for i in range(20):
    run(pl({"file_path": os.path.join(repo_t, "a")}, repo_t, session="A"))
leftovers = [f for f in os.listdir(os.path.join(repo_t, "state")) if ".tmp." in f]
check("no orphaned .tmp.* files accumulate in state/", leftovers == [], leftovers)

# =====================================================================
# 13. Key normalization: separator/trailing-slash variants of the SAME tree
#     resolve to one owner key (so the 2nd session is blocked) on every OS.
# =====================================================================
repo_k = new_main_tree(); wt_k = new_worktree(repo_k, "wt")  # blocking is worktree-scoped
run(pl({"file_path": "a"}, wt_k, session="A"))
variant = wt_k.rstrip("/\\") + os.sep + "sub" + os.sep + ".." + os.sep  # same tree via ./.. roundtrip
rc, _, err = run(pl({"file_path": "a"}, variant, session="B"))
check("separator/.. variant of same tree -> 2nd session blocked", blocked(rc, err), f"rc={rc}")
# Case variance: blocked on a case-insensitive FS (Windows); distinct tree on a
# case-sensitive FS (Linux) -> allowed. Assert per platform.
if os.path.normcase("A") == os.path.normcase("a"):
    rc, _, err = run(pl({"file_path": "a"}, wt_k.upper(), session="C"))
    check("case-insensitive FS: upper-case spelling of same tree blocked", blocked(rc, err), f"rc={rc}")

# Windows \\?\ extended-length prefix is a pure alias and must be stripped so the
# prefixed spelling keys to the SAME tree (closes the round-3 \\?\ bypass without
# resolving symlinks). Windows-only (the prefix is meaningless on POSIX).
if os.name == "nt":
    repo_x = new_main_tree(); wt_x = new_worktree(repo_x, "wt")  # blocking is worktree-scoped
    run(pl({"file_path": "a"}, wt_x, session="A"))
    ext = "\\\\?\\" + os.path.abspath(wt_x)
    rc, _, err = run(pl({"file_path": "a"}, ext, session="B"))
    check("\\\\?\\ extended-length spelling of same tree -> 2nd session blocked",
          blocked(rc, err), f"rc={rc}")

# =====================================================================
# 14. MAIN-checkout concurrent-session detection -> NON-BLOCKING WARNING.
#     Main BLOCKING is unsound (a churned/ghost transcript is indistinguishable
#     from a real peer by mtime -- auditor 2026-06-18), so the hook WARNS instead:
#     exit 0 + a JSON systemMessage on stdout. A false warning is harmless, which is
#     why this is sound where a block was not. newer-than-mine is only a NOISE
#     reducer. Worktree/owner-map logic is untouched (sections 1-13 pass no
#     transcript_path, so this path stays inert for them).
# =====================================================================
repo_m = new_main_tree()


def main_call(bucket, sid="S", mine="MINE.jsonl", env_extra=None):
    return run(pl({"file_path": os.path.join(repo_m, "f")}, repo_m,
                  session=sid, transcript=os.path.join(bucket, mine)),
               env_extra=env_extra)


# (b) genuine concurrent peer (newer than mine, in window) -> WARN, never block
b = bucket_with([("MINE.jsonl", 60), ("PEER.jsonl", 8)])
rc, out, _ = main_call(b)
check("main: concurrent live peer -> WARNS (exit 0 + systemMessage onboarding to a worktree)",
      warned(rc, out), f"rc={rc} out={out[:140]}")

# (SAFETY) the case the BLOCK version got wrong (auditor finding 2): my OWN churned
# ghost is NEWER than my current transcript (trailing write / un-flushed new). A
# block SELF-LOCKED here; warn-only must NEVER exit 2 -- a harmless warning is fine.
b = bucket_with([("MINE.jsonl", 30), ("MY_GHOST.jsonl", 5)])  # ghost newer than mine
rc, out, err = main_call(b)
check("main: own ghost NEWER than mine -> NOT blocked (no self-lockout)", rc == 0, f"rc={rc} err={err[:80]}")

# (a/d) older sibling (own older ghost / idle peer I'm ahead of) -> silent (noise filter)
b = bucket_with([("MINE.jsonl", 60), ("OLDID.jsonl", 120)])
rc, out, _ = main_call(b)
check("main: older sibling -> silent allow (no warning noise)", silent(rc, out), f"rc={rc} out={out[:140]}")

# (e) window bound: newer-than-mine but beyond the window -> silent
b = bucket_with([("MINE.jsonl", 1200), ("DEAD.jsonl", 600)])
rc, out, _ = main_call(b)
check("main: newer-but-stale peer (beyond window) -> silent allow", silent(rc, out), f"rc={rc}")

# (g) only my own transcript present -> silent
b = bucket_with([("MINE.jsonl", 5)])
rc, out, _ = main_call(b)
check("main: only my own transcript -> silent allow", silent(rc, out), f"rc={rc}")

# (c) fail-open: transcript_path present but its dir does not exist -> silent (never
#     warn because of the guard's OWN failure)
rc, out, _ = run(pl({"file_path": os.path.join(repo_m, "f")}, repo_m, session="S",
                    transcript=os.path.join(tempfile.gettempdir(), "guardb_no_such_dir_zzz", "x.jsonl")))
check("main: unreadable transcript dir -> silent allow (fail-safe)", silent(rc, out), f"rc={rc}")

# (h) hatch short-circuits before detection -> silent even with a live peer present
b = bucket_with([("MINE.jsonl", 60), ("PEER.jsonl", 8)])
rc, out, _ = main_call(b, env_extra={"HARNESS_ALLOW_MULTI_SESSION": "1"})
check("main: HARNESS_ALLOW_MULTI_SESSION=1 -> silent allow (no warning)", silent(rc, out), f"rc={rc}")

# (i) a WORKTREE is unaffected by transcript detection (it blocks via the owner map,
#     not transcripts): a fresh peer transcript must not change a worktree's own
#     first-session-allowed behavior.
repo_w = new_main_tree(); wt_w = new_worktree(repo_w, "wt")
bw = bucket_with([("MINE.jsonl", 5), ("PEER.jsonl", 2)])
rc, _, _ = run(pl({"file_path": os.path.join(wt_w, "a")}, wt_w, session="W",
                  transcript=os.path.join(bw, "MINE.jsonl")))
check("worktree: transcript detection does NOT apply (first session still allowed)", rc == 0, f"rc={rc}")

# =====================================================================
# 15. Warn-throttle cooldown (auditor 6a / follow-up 10fc0b): a live peer must WARN
#     at most once per _WARN_COOLDOWN_SECONDS, not on every PreToolUse. The hook
#     stamps last_warn_ts in the owner map on warn, suppresses re-warns within the
#     window, and resumes once it lapses. (Buckets are rebuilt each call so PEER
#     stays in-window & newer-than-mine against the live clock; only the cooldown,
#     not peer liveness, changes the outcome between calls.)
# =====================================================================
repo_th = new_main_tree()
TH_COOLDOWN = 180  # mirrors _WARN_COOLDOWN_SECONDS (== _CONCURRENT_WINDOW_SECONDS)


def th_call(sid="TH"):
    bkt = bucket_with([("MINE.jsonl", 60), ("PEER.jsonl", 8)])  # peer fresh & newer
    return run(pl({"file_path": os.path.join(repo_th, "f")}, repo_th,
                  session=sid, transcript=os.path.join(bkt, "MINE.jsonl")))


rc, out, _ = th_call()
check("throttle: first peer encounter WARNS", warned(rc, out), f"rc={rc} out={out[:120]}")
check("throttle: last_warn_ts stamped in the owner map on warn",
      isinstance((owner_of(repo_th) or {}).get("last_warn_ts"), (int, float)),
      read_map(repo_th))

rc, out, _ = th_call()
check("throttle: re-warn WITHIN cooldown is suppressed (silent)", silent(rc, out),
      f"rc={rc} out={out[:120]}")
check("throttle: suppressed call keeps the same owner (still claimed)",
      (owner_of(repo_th) or {}).get("session_id") == "TH", read_map(repo_th))

# Age the stamped last_warn_ts past the cooldown -> the next live peer WARNS again.
_m = read_map(repo_th)
_m[_key(repo_th)]["last_warn_ts"] = time.time() - (TH_COOLDOWN + 10)
with open(os.path.join(repo_th, MAP_REL), "w") as f:
    json.dump(_m, f)
rc, out, _ = th_call()
check("throttle: re-warn AFTER cooldown lapses fires again", warned(rc, out),
      f"rc={rc} out={out[:120]}")

# A churned session_id (its own entry no longer session-matches) resets the cooldown
# -> warns once immediately rather than inheriting the predecessor's clock.
rc, out, _ = th_call(sid="TH_NEW")
check("throttle: a churned/new session_id re-warns once (cooldown reset)",
      warned(rc, out), f"rc={rc} out={out[:120]}")

# =====================================================================
# 16. Fix B (2026-06-18): Guard B no-ops in a FOREIGN repo (repo != HARNESS_ROOT) and
#     writes NO state/ there. Uses the REAL hook (HARNESS_ROOT == this repo) against a
#     cwd in an unrelated temp repo with no installed copy -> the production scope no-op.
# =====================================================================
_foreign = tempfile.mkdtemp(prefix="guardb_foreign_"); _TMPDIRS.append(_foreign)
os.mkdir(os.path.join(_foreign, ".git"))  # a real repo, but NOT the harness; no hook copy
rc, _out, err = run(pl({"file_path": os.path.join(_foreign, "x.py")}, _foreign, session="A"))
check("foreign repo: Guard B scope no-op (exit 0)", rc == 0, f"rc={rc} err={err[:80]}")
check("foreign repo: NO state/ written into the foreign tree (Gap B fixed)",
      not os.path.exists(os.path.join(_foreign, "state")), os.listdir(_foreign))
# SessionEnd / SessionStart in a foreign repo must also no-op (never write state/).
run(pl({}, _foreign, session="A", event="SessionEnd", tool=""))
run(pl({}, _foreign, session="B", event="SessionStart", tool="", source="startup"))
check("foreign repo: SessionEnd/Start also write no state/",
      not os.path.exists(os.path.join(_foreign, "state")), os.listdir(_foreign))

for d in _TMPDIRS:
    shutil.rmtree(d, ignore_errors=True)

print(f"\n{'ALL TESTS PASS' if not FAILURES else str(len(FAILURES)) + ' FAILURES: ' + ', '.join(FAILURES)}")


def test_suite_passes():
    assert not FAILURES, f"{len(FAILURES)} failures: {', '.join(FAILURES)}"


if __name__ == "__main__":
    sys.exit(1 if FAILURES else 0)
