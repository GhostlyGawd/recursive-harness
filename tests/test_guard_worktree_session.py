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
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.environ.get(
    "GUARD_B_HOOK", os.path.join(ROOT, "hooks", "guard_worktree_session.py")
)
MAP_REL = os.path.join("state", "session_owners.json")
FAILURES = []
_TMPDIRS = []


def run(payload, env_extra=None):
    env = dict(os.environ)
    env.pop("HARNESS_ALLOW_MULTI_SESSION", None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def pl(tool_input, cwd, session="s1", event="PreToolUse", tool="Read", source=None):
    p = {"hook_event_name": event, "tool_name": tool,
         "tool_input": tool_input, "cwd": cwd, "session_id": session}
    if source is not None:
        p["source"] = source
    return p


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def blocked(rc, err):
    low = err.lower()
    return rc == 2 and "blocked" in low and "worktree" in low


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


def new_main_tree():
    """Fake main checkout: a temp dir holding a `.git` DIRECTORY."""
    d = tempfile.mkdtemp(prefix="guardb_main_")
    _TMPDIRS.append(d)
    os.mkdir(os.path.join(d, ".git"))
    return d


def new_worktree(repo, name="wt-a"):
    """Fake linked worktree `<repo>/.claude/worktrees/<name>` holding a `.git` FILE."""
    wt = os.path.join(repo, ".claude", "worktrees", name)
    os.makedirs(wt, exist_ok=True)
    with open(os.path.join(wt, ".git"), "w") as f:
        f.write("gitdir: /dev/null\n")
    return wt


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
# 2. Scope: the MAIN checkout is guarded too (user decision 2026-06-17)
# =====================================================================
repo2 = new_main_tree()
rc, _, _ = run(pl({"file_path": os.path.join(repo2, "f.py")}, repo2, session="A"))
check("main checkout: first session A allowed", rc == 0, f"rc={rc}")

rc, _, err = run(pl({"file_path": os.path.join(repo2, "f.py")}, repo2, session="B"))
check("main checkout: second session B blocked (scope=main+worktrees)",
      blocked(rc, err), f"rc={rc}")

sub = os.path.join(repo2, "skills")
os.makedirs(sub, exist_ok=True)
rc, _, err = run(pl({"file_path": os.path.join(sub, "g.py")}, sub, session="C"))
check("main checkout: subdir session resolves to same tree -> blocked",
      blocked(rc, err), f"rc={rc}")

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
repo3 = new_main_tree()
rc, _, _ = run(pl({"file_path": os.path.join(repo3, "a")}, repo3, session="OLD"))
check("ttl: OLD claims tree", rc == 0, f"rc={rc}")
backdate(repo3, 10 * 24 * 3600)
rc, _, _ = run(pl({"file_path": os.path.join(repo3, "a")}, repo3, session="NEW"))
check("ttl: stale owner taken over by NEW (allowed)", rc == 0, f"rc={rc}")
check("ttl: NEW is now the owner", (owner_of(repo3) or {}).get("session_id") == "NEW", read_map(repo3))
rc, _, err = run(pl({"file_path": os.path.join(repo3, "a")}, repo3, session="LATE"))
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
repo5 = new_main_tree()
run(pl({"file_path": os.path.join(repo5, "a")}, repo5, session="HOLD"))
for val in ("1", "true", "YES", "on"):
    rc, _, _ = run(pl({"file_path": os.path.join(repo5, "a")}, repo5, session="X"),
                   env_extra={"HARNESS_ALLOW_MULTI_SESSION": val})
    check(f"hatch ={val!r} enables bypass", rc == 0, f"rc={rc}")
for val in ("0", "false", "no", "off", ""):
    rc, _, err = run(pl({"file_path": os.path.join(repo5, "a")}, repo5, session="X"),
                     env_extra={"HARNESS_ALLOW_MULTI_SESSION": val})
    check(f"hatch ={val!r} does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")
# Regression (harness-auditor 2026-06-17): the TTL must NOT be env-overridable —
# a tiny HARNESS_SESSION_TTL_SECONDS would be a self-assertable bypass (instantly
# stale-out + evict the live owner). It must be ignored entirely; the 2nd session
# still blocks regardless of the value.
for val in ("0", "0.0001", "1", "-5", "99999999"):
    rc, _, err = run(pl({"file_path": os.path.join(repo5, "a")}, repo5, session="ATK"),
                     env_extra={"HARNESS_SESSION_TTL_SECONDS": val})
    check(f"TTL env override ={val!r} is NOT honored (no self-assertable bypass)",
          blocked(rc, err), f"rc={rc}")

# =====================================================================
# 7. Tool-agnostic block + onboarding message content
# =====================================================================
repo6 = new_main_tree()
run(pl({"file_path": os.path.join(repo6, "a")}, repo6, session="OWN"))
for tool, ti in (("Edit", {"file_path": os.path.join(repo6, "a")}),
                 ("Write", {"file_path": os.path.join(repo6, "a")}),
                 ("Bash", {"command": "ls"}),
                 ("Grep", {"pattern": "x", "path": repo6}),
                 ("Glob", {"pattern": "**/*", "path": repo6})):
    rc, _, err = run(pl(ti, repo6, session="B", tool=tool))
    check(f"second session blocked on {tool}", blocked(rc, err), f"rc={rc}")
rc, _, _ = run(pl({"command": "ls"}, repo6, session="OWN", tool="Bash"))
check("owner allowed on Bash (heartbeat)", rc == 0, f"rc={rc}")
_, _, err = run(pl({"file_path": os.path.join(repo6, "a")}, repo6, session="B"))
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

repo_s = new_main_tree()
run(pl({"file_path": os.path.join(repo_s, "a")}, repo_s, session="LIVE"))
rc, _, _ = run(pl({}, repo_s, session="OTHER", event="SessionStart", tool="", source="startup"))
check("SessionStart source=startup does NOT release", rc == 0, f"rc={rc}")
check("SessionStart startup left the live owner intact",
      (owner_of(repo_s) or {}).get("session_id") == "LIVE", read_map(repo_s))
rc, _, err = run(pl({"file_path": os.path.join(repo_s, "a")}, repo_s, session="OTHER"))
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
p = subprocess.run([sys.executable, HOOK], input="not json{{", capture_output=True, text=True)
check("fails open on garbage stdin", p.returncode == 0, f"rc={p.returncode}")

deep = "[" * 6000 + "]" * 6000  # RecursionError in json.load — must still exit 0
p = subprocess.run([sys.executable, HOOK], input=deep, capture_output=True, text=True)
check("deeply-nested JSON fails OPEN (exit 0, not 1)", p.returncode == 0, f"rc={p.returncode} err={p.stderr[:60]}")

deep_payload = '{"session_id":"A","cwd":"/x","hook_event_name":"PreToolUse","tool_input":' + "[" * 6000 + "]" * 6000 + "}"
p = subprocess.run([sys.executable, HOOK], input=deep_payload, capture_output=True, text=True)
check("deeply-nested value inside a real payload fails OPEN (exit 0)", p.returncode == 0, f"rc={p.returncode}")

repo7 = new_main_tree()
payload = {"hook_event_name": "PreToolUse", "tool_name": "Read",
           "tool_input": {"file_path": os.path.join(repo7, "a")}, "cwd": repo7}
rc, _, _ = run(payload)
check("missing session_id fails open (allowed)", rc == 0, f"rc={rc}")
check("missing session_id did NOT write any owner", owner_of(repo7) is None, read_map(repo7))

rc, _, _ = run(pl({"file_path": os.path.join(repo7, "a")}, repo7, session=""))
check("blank session_id fails open (allowed)", rc == 0, f"rc={rc}")

p = subprocess.run([sys.executable, HOOK], input='["a","b"]', capture_output=True, text=True)
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
repo_k = new_main_tree()
run(pl({"file_path": "a"}, repo_k, session="A"))
variant = repo_k.rstrip("/\\") + os.sep + "skills" + os.sep + ".." + os.sep  # same tree via ./.. roundtrip
rc, _, err = run(pl({"file_path": "a"}, variant, session="B"))
check("separator/.. variant of same tree -> 2nd session blocked", blocked(rc, err), f"rc={rc}")
# Case variance: blocked on a case-insensitive FS (Windows); distinct tree on a
# case-sensitive FS (Linux) -> allowed. Assert per platform.
if os.path.normcase("A") == os.path.normcase("a"):
    rc, _, err = run(pl({"file_path": "a"}, repo_k.upper(), session="C"))
    check("case-insensitive FS: upper-case spelling of same tree blocked", blocked(rc, err), f"rc={rc}")

# Windows \\?\ extended-length prefix is a pure alias and must be stripped so the
# prefixed spelling keys to the SAME tree (closes the round-3 \\?\ bypass without
# resolving symlinks). Windows-only (the prefix is meaningless on POSIX).
if os.name == "nt":
    repo_x = new_main_tree()
    run(pl({"file_path": "a"}, repo_x, session="A"))
    ext = "\\\\?\\" + os.path.abspath(repo_x)
    rc, _, err = run(pl({"file_path": "a"}, ext, session="B"))
    check("\\\\?\\ extended-length spelling of same tree -> 2nd session blocked",
          blocked(rc, err), f"rc={rc}")

for d in _TMPDIRS:
    shutil.rmtree(d, ignore_errors=True)

print(f"\n{'ALL TESTS PASS' if not FAILURES else str(len(FAILURES)) + ' FAILURES: ' + ', '.join(FAILURES)}")


def test_suite_passes():
    assert not FAILURES, f"{len(FAILURES)} failures: {', '.join(FAILURES)}"


if __name__ == "__main__":
    sys.exit(1 if FAILURES else 0)
