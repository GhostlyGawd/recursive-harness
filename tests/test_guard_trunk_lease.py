#!/usr/bin/env python3
r"""Tests for guard_trunk_lease.py (Guard C) — the trunk HEAD lease.

Contract (a PreToolUse + PostToolUse hook):
  Input JSON: {tool_name, tool_input, cwd, session_id, hook_event_name}
  PreToolUse on a MUTATING op (Edit/Write/MultiEdit/NotebookEdit, or a
  tree-mutating Bash/PowerShell command) BLOCKS (exit 2 + stderr 'BLOCKED'/'trunk')
  when the trunk fingerprint (HEAD sym-ref + oid + dirty hash) differs from THIS
  session's OWN last-seen lease. PostToolUse re-stamps my last-seen. Reads, a
  bootstrap (no lease — incl. session_id churn), an unchanged tree, a worktree cwd,
  a non-harness checkout (no state/), and the HARNESS_TRUNK_LEASE_OK hatch all ALLOW
  (exit 0). Fails OPEN on malformed input.

Block-cases assert 'blocked' AND 'trunk' in stderr so a MISSING hook (exits 2 with
a 'No such file' error) cannot satisfy them — keeps red honest.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "guard_trunk_lease.py")
FAILURES = []


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def run(payload, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, env=env, timeout=10)
    return p.returncode, p.stdout, p.stderr


def pl(tool, ti, cwd, sid="s1", event="PreToolUse"):
    return {"tool_name": tool, "tool_input": ti, "cwd": cwd,
            "session_id": sid, "hook_event_name": event}


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAILURES.append(name)


def blocked(rc, err):
    low = err.lower()
    return rc == 2 and "blocked" in low and "trunk" in low


def mkrepo(gitignore_state=True, with_state=True):
    """A temp git repo shaped like the harness trunk: branch main, one commit, a
    gitignored state/ dir (so lease writes never perturb the dirty fingerprint)."""
    d = tempfile.mkdtemp(prefix="trunklease-")
    git(["init", "-q", "-b", "main"], d)
    git(["config", "user.email", "t@t.test"], d)
    git(["config", "user.name", "t"], d)
    with open(os.path.join(d, "README.md"), "w") as f:
        f.write("x\n")
    if gitignore_state:
        with open(os.path.join(d, ".gitignore"), "w") as f:
            f.write("state/\n")
    git(["add", "-A"], d)
    git(["commit", "-q", "-m", "init"], d)
    if with_state:
        os.makedirs(os.path.join(d, "state"), exist_ok=True)
    return d


def stamp(repo, sid):
    """Establish `sid`'s last-seen at the current tree state via a PostToolUse."""
    return run(pl("Edit", {"file_path": os.path.join(repo, "x")}, repo,
                  sid=sid, event="PostToolUse"))


REPOS = []


def fresh(**kw):
    r = mkrepo(**kw)
    REPOS.append(r)
    return r


try:
    EDIT = lambda repo: {"file_path": os.path.join(repo, "f.py")}

    # --- 1. bootstrap: first mutating op with no lease -> ALLOW + lease written ---
    r = fresh()
    rc, _, _ = run(pl("Edit", EDIT(r), r, sid="A"))
    check("bootstrap (no lease) Edit ALLOWED", rc == 0, f"rc={rc}")
    check("bootstrap wrote a lease dir", os.path.isdir(os.path.join(r, "state", "trunk-lease")))

    # --- 2. steady-state: after a stamp, unchanged tree -> ALLOW (lease write in
    #         gitignored state/ must NOT perturb the dirty fingerprint) ---
    r = fresh()
    stamp(r, "A")
    rc, _, _ = run(pl("Edit", EDIT(r), r, sid="A"))
    check("unchanged tree after stamp ALLOWED (state/ gitignored)", rc == 0, f"rc={rc}")

    # --- 3. peer interleaving: A stamps at X; HEAD moves (peer); A's next op BLOCKS ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "peerbranch"], r)   # simulate a 2nd session switching HEAD
    rc, _, err = run(pl("Edit", EDIT(r), r, sid="A"))
    check("peer moved HEAD -> A's next mutating op BLOCKED", blocked(rc, err), f"rc={rc} err={err[:70]}")
    check("peer-moved-HEAD block blames a peer", "another session" in err.lower(), err[:90])

    # --- 3b. peer made an uncommitted edit to a TRACKED file -> BLOCK (a tracked
    #         change is real, clobberable divergence; HEAD unchanged, so the message
    #         must NOT blame a peer) ---
    r = fresh()
    stamp(r, "A")
    with open(os.path.join(r, "README.md"), "w") as f:
        f.write("peer edited a tracked file\n")
    rc, _, err = run(pl("Write", {"file_path": os.path.join(r, "mine.py")}, r, sid="A"))
    check("peer edited a TRACKED file -> A BLOCKED", blocked(rc, err), f"rc={rc}")
    check("tracked-dirty block does NOT blame a phantom peer (HEAD unchanged)",
          "another session" not in err.lower() and "head is unchanged" in err.lower(), err[:100])

    # --- 3c. CALIBRATION (2026-06-19): a NEW UNTRACKED file/dir must NOT block. A
    #         session's own background-subagent output, a pre-ignore build artifact, or
    #         `.claude/` first materializing flipped the dirty hash with HEAD unchanged
    #         and produced phantom-peer self-blocks (the 3x self-block that day).
    #         Untracked can't be clobbered by a peer the way tracked/index state can,
    #         so it is excluded from the dirty fingerprint. ---
    r = fresh()
    stamp(r, "A")
    with open(os.path.join(r, "scratch_untracked.txt"), "w") as f:
        f.write("subagent output\n")
    rc, _, _ = run(pl("Edit", EDIT(r), r, sid="A"))
    check("new UNTRACKED file does NOT block (no phantom-peer self-block)", rc == 0, f"rc={rc}")
    os.makedirs(os.path.join(r, "newdir_untracked"))
    with open(os.path.join(r, "newdir_untracked", "a.txt"), "w") as f:
        f.write("y\n")
    rc, _, _ = run(pl("Edit", EDIT(r), r, sid="A"))
    check("new top-level UNTRACKED dir does NOT block", rc == 0, f"rc={rc}")

    # --- 4. session_id CHURN must NOT false-lock: A stamps at X; a NEW sid A' acts
    #         on the SAME unchanged tree -> bootstrap -> ALLOW (the ADR-0007 guard) ---
    r = fresh()
    stamp(r, "A")
    rc, _, _ = run(pl("Edit", EDIT(r), r, sid="A-prime-churned"))
    check("churned successor (new sid, unchanged tree) ALLOWED (no false-lock)", rc == 0, f"rc={rc}")

    # --- 5. inline hatch re-baselines: A stamps at X; HEAD moves; A proceeds with
    #         HARNESS_TRUNK_LEASE_OK=1 -> ALLOW; then A's next op at new state ALLOWED ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "other"], r)
    rc, _, _ = run(pl("Bash", {"command": "HARNESS_TRUNK_LEASE_OK=1 git commit --allow-empty -m x"}, r, sid="A"))
    check("inline hatch on mismatch ALLOWED (re-baseline)", rc == 0, f"rc={rc}")
    rc, _, _ = run(pl("Bash", {"command": "git commit --allow-empty -m y"}, r, sid="A"))
    check("after hatch re-baseline, next op at new state ALLOWED", rc == 0, f"rc={rc}")

    # --- 5b. an inert/quoted MENTION of the hatch does NOT enable it (still blocks) ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "z"], r)
    rc, _, err = run(pl("Bash", {"command": 'echo "HARNESS_TRUNK_LEASE_OK=1"; git commit --allow-empty -m x'}, r, sid="A"))
    check("quoted/inert hatch mention does NOT bypass (still blocks)", blocked(rc, err), f"rc={rc}")

    # --- 6. env hatch disables the guard for the session (mismatch -> ALLOW) ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "w"], r)
    rc, _, _ = run(pl("Edit", EDIT(r), r, sid="A"),
                   env_extra={"HARNESS_TRUNK_LEASE_OK": "1"})
    check("env hatch disables guard (mismatch ALLOWED)", rc == 0, f"rc={rc}")
    rc, _, err = run(pl("Edit", EDIT(r), r, sid="A"),
                     env_extra={"HARNESS_TRUNK_LEASE_OK": "0"})
    check("env hatch =0 does NOT disable (still blocks)", blocked(rc, err), f"rc={rc}")

    # --- 7. READS are never gated: a non-mutating Bash + a Read, even on a mismatch ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "v"], r)        # tree moved
    rc, _, _ = run(pl("Bash", {"command": "git status && ls"}, r, sid="A"))
    check("non-mutating Bash NOT gated on mismatch (read allowed)", rc == 0, f"rc={rc}")
    rc, _, _ = run(pl("Read", {"file_path": os.path.join(r, "README.md")}, r, sid="A"))
    check("Read NOT gated on mismatch", rc == 0, f"rc={rc}")
    # ...but a mutating Bash on the same mismatch DOES block.
    rc, _, err = run(pl("Bash", {"command": "git commit --allow-empty -m z"}, r, sid="A"))
    check("mutating Bash on mismatch BLOCKED", blocked(rc, err), f"rc={rc}")

    # --- 8. worktree cwd is Guard B's job -> Guard C skips (ALLOW even on mismatch) ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "u"], r)
    wt_cwd = os.path.join(r, ".claude", "worktrees", "wt-x")
    rc, _, _ = run(pl("Edit", {"file_path": os.path.join(wt_cwd, "f")}, wt_cwd, sid="A"))
    check("worktree cwd skipped (Guard B governs)", rc == 0, f"rc={rc}")

    # --- 9. no state/ dir -> not harness-shaped -> skip (don't litter foreign repos) ---
    r = fresh(with_state=False)
    stamp(r, "A")                                 # no-op stamp (no state/, nothing written)
    git(["checkout", "-q", "-b", "t2"], r)
    rc, _, _ = run(pl("Edit", EDIT(r), r, sid="A"))
    check("no state/ dir -> skipped (ALLOW, no lease)", rc == 0, f"rc={rc}")
    check("no lease dir created in non-harness repo",
          not os.path.isdir(os.path.join(r, "state", "trunk-lease")))

    # --- 10. fail OPEN on garbage stdin ---
    p = subprocess.run([sys.executable, HOOK], input="not json{{", capture_output=True, text=True)
    check("fails open on garbage stdin", p.returncode == 0, f"rc={p.returncode}")

    # --- 11. PostToolUse never blocks (always exit 0), even on a mismatch ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "s2"], r)
    rc, _, _ = run(pl("Edit", EDIT(r), r, sid="A", event="PostToolUse"))
    check("PostToolUse never blocks (stamps, exit 0)", rc == 0, f"rc={rc}")

    # --- 12. two distinct live sessions, bidirectional detection: A and B both
    #         bootstrap at X; A switches HEAD; B (stale lease) is BLOCKED next op ---
    r = fresh()
    stamp(r, "A")
    stamp(r, "B")
    git(["checkout", "-q", "-b", "afork"], r)     # A moved HEAD (A would re-stamp via PostToolUse)
    run(pl("Edit", EDIT(r), r, sid="A", event="PostToolUse"))  # A advances its lease
    rc, _, err = run(pl("Edit", EDIT(r), r, sid="B"))          # B still at X -> BLOCK
    check("bidirectional: B blocked after A moved HEAD", blocked(rc, err), f"rc={rc}")

    # --- 13. FIX-B: even when state/ is NOT gitignored, a lease write must NOT
    #         self-perturb the fingerprint -> no constant self-block (state/ is
    #         stripped from the dirty hash). Without the fix this bricks. ---
    r = fresh(gitignore_state=False)
    stamp(r, "A")                                 # writes a lease into the non-ignored state/
    rc, _, _ = run(pl("Edit", EDIT(r), r, sid="A"))
    check("non-gitignored state/ does NOT self-brick (FIX-B)", rc == 0, f"rc={rc}")

    # --- 14. REGRESSION (session f36989d6, 2026-06-21): the classifier must recognize git
    #         GLOBAL OPTIONS before the subcommand. commands/harness-pr.md + retro.md mandate the
    #         `git -C "$HARNESS" <subcmd>` form; when it was treated as a READ, HEAD-moving ops
    #         never re-stamped AND a leading inline hatch silently no-opped (hatch sits behind
    #         _is_mutating). A whole /retro+PR session was lost to repeated false blocks. ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "gc1"], r)        # HEAD moved since A's stamp
    rc, _, err = run(pl("Bash", {"command": f'git -C "{r}" commit --allow-empty -m x'}, r, sid="A"))
    check("git -C <path> <mutating-subcmd> classified mutating (blocks on mismatch)", blocked(rc, err), f"rc={rc}")
    rc, _, _ = run(pl("Bash", {"command": f'git -C "{r}" status'}, r, sid="A"))
    check("git -C <path> <read-subcmd> still NOT gated", rc == 0, f"rc={rc}")
    rc, _, _ = run(pl("Bash", {"command": f'HARNESS_TRUNK_LEASE_OK=1 git -C "{r}" commit --allow-empty -m y'}, r, sid="A"))
    check("inline hatch on a git -C command re-baselines (ALLOW)", rc == 0, f"rc={rc}")
    rc, _, _ = run(pl("Bash", {"command": f'git -C "{r}" merge --ff-only nope'}, r, sid="A"))
    check("after hatch re-baseline, next git -C mutating op at same state ALLOWED", rc == 0, f"rc={rc}")

    # --- 15. NIT-A (followup 512398): a `git branch` READ (-a/-vv/-r/--list) must NOT be
    #         classified mutating. The old `branch\s+-[a-zA-Z]` clause flagged EVERY dashed
    #         branch flag, so a harmless `git branch -a` on a moved tree drew a (recoverable
    #         but noisy) lease BLOCK. Only ref-MUTATING branch ops should gate. ---
    for readcmd in ("git branch -a", "git branch -vv", "git branch -r", "git branch --list"):
        r = fresh()
        stamp(r, "A")
        git(["checkout", "-q", "-b", "nb-" + readcmd.split()[-1].strip("-")], r)  # tree moved
        rc, _, _ = run(pl("Bash", {"command": readcmd}, r, sid="A"))
        check(f"NIT-A: '{readcmd}' is a READ, not gated on mismatch", rc == 0, f"rc={rc}")
    # ...and a ref-MUTATING branch op on the same mismatch DOES still block.
    for mutcmd in ("git branch -D gone", "git branch -m old new", "git branch --delete x"):
        r = fresh()
        stamp(r, "A")
        git(["checkout", "-q", "-b", "mb-x"], r)
        rc, _, err = run(pl("Bash", {"command": mutcmd}, r, sid="A"))
        check(f"NIT-A: '{mutcmd}' still classified mutating (blocks on mismatch)", blocked(rc, err), f"rc={rc}")

    # --- 15b. NIT-B (followup 512398) regression: the f36989d6 global-option fix already
    #          classifies `git -C "<quoted space>" -c k=v <mutating>` as mutating (it was a
    #          documented KNOWN-GAP under-classify, now closed). Lock it so it can't regress. ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "nitb"], r)
    rc, _, err = run(pl("Bash", {"command": f'git -C "{r}" -c user.name=x commit --allow-empty -m z'}, r, sid="A"))
    check("NIT-B: git -C <quoted-space> -c k=v commit classified mutating (blocks)", blocked(rc, err), f"rc={rc}")

    # --- 16. f963e5: the trunk-moved BLOCK hint must name the subagent/pinned-cwd escape
    #         (spawn an isolation:worktree Agent), not only EnterWorktree -- the guard fires
    #         in exactly the pinned/subagent context where EnterWorktree is unavailable. ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "hintb"], r)
    rc, _, err = run(pl("Edit", EDIT(r), r, sid="A"))
    check("f963e5: block hint names the isolation-agent escape for pinned/subagent sessions",
          "isolation" in err.lower(), err[-160:])

    # --- 17. GAP (a /gc run, 2026-06-28): `git add` was MISSING from the
    #         mutating-subcommand classifier. A /gc run does python-writes (untracked, excluded
    #         from the fingerprint) then `git add <paths>` (which STAGES them -> the tracked/index
    #         dirty hash flips) then `git commit`. With `git add` mis-classified a READ, its
    #         PostToolUse never re-stamped, so the commit's PreToolUse compared the now-staged tree
    #         against a stale clean lease and BLOCKED the session against its OWN staged change.
    #         `git add` mutates the index -> it must be gated (so PostToolUse re-stamps). Read-only
    #         `git status`/`git diff` stay ungated (covered above). ---
    for addcmd in ("git add -A", "git add .", "git add memory/heal/"):
        r = fresh()
        stamp(r, "A")
        git(["checkout", "-q", "-b", "add-" + addcmd.split()[-1].strip("-./")], r)  # HEAD moved since A's stamp
        rc, _, err = run(pl("Bash", {"command": addcmd}, r, sid="A"))
        check(f"git add classified mutating: '{addcmd}' blocks on mismatch", blocked(rc, err), f"rc={rc}")
    # ...incl. the mandated `git -C "<path>" add` global-options form (commands/harness-pr.md).
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "addc"], r)
    rc, _, err = run(pl("Bash", {"command": f'git -C "{r}" add -A'}, r, sid="A"))
    check("git -C <path> add classified mutating (blocks on mismatch)", blocked(rc, err), f"rc={rc}")
    # END-TO-END repro of the /gc self-block: stamp; an OWN `git add` re-stamps via PostToolUse;
    # the following commit at the same staged tree is ALLOWED. RED before the fix (add's PostToolUse
    # returns early as a non-mutating READ -> no re-stamp -> commit blocks against my own staging).
    r = fresh()
    stamp(r, "A")
    with open(os.path.join(r, "newfile.txt"), "w") as f:
        f.write("x\n")
    git(["add", "-A"], r)                                       # ACTUALLY stage it: the tree now has a
                                                                # real tracked/index change (a flipped dirty hash)
    run(pl("Bash", {"command": "git add -A"}, r, sid="A", event="PostToolUse"))  # add's PostToolUse re-stamps
    rc, _, err = run(pl("Bash", {"command": "git commit -m x"}, r, sid="A"))     # commit's PreToolUse check
    check("after `git add` re-stamps, the follow-up commit is ALLOWED (no self-block)", rc == 0, f"rc={rc} err={err[:60]}")

    # --- 18. SECURITY (2026-07-17 CodeQL py/redos alerts 2 + 3): repeated `-c`
    #         options in hook-controlled input must classify in linear time. The old regex
    #         could backtrack exponentially over both unquoted and empty-quoted values. ---
    r = fresh()
    stamp(r, "A")
    git(["checkout", "-q", "-b", "redos"], r)
    started = time.monotonic()
    rc, _, _ = run(pl("Bash", {"command": "git " + "-c ! " * 5000 + "status"}, r, sid="A"))
    elapsed = time.monotonic() - started
    check("adversarial unquoted git options stay bounded and read-only",
          rc == 0 and elapsed < 8, f"rc={rc} elapsed={elapsed:.3f}s")
    started = time.monotonic()
    rc, _, err = run(pl("Bash", {"command": "git " + '-c "" ' * 5000 + "commit"}, r, sid="A"))
    elapsed = time.monotonic() - started
    check("adversarial quoted git options stay bounded and mutating",
          blocked(rc, err) and elapsed < 8, f"rc={rc} elapsed={elapsed:.3f}s")
    rc, _, _ = run(pl("Bash", {"command": 'echo "git commit"'}, r, sid="A"))
    check("quoted git text is inert, not a mutating command", rc == 0, f"rc={rc}")
    rc, _, err = run(pl("Bash", {"command": "echo ok; git commit -m x"}, r, sid="A"))
    check("compound command still finds a real git mutator", blocked(rc, err), f"rc={rc}")

finally:
    for d in REPOS:
        try:
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass

print(f"\n{'ALL TESTS PASS' if not FAILURES else str(len(FAILURES)) + ' FAILURES: ' + ', '.join(FAILURES)}")


def test_suite_passes():
    assert not FAILURES, f"{len(FAILURES)} failures: {', '.join(FAILURES)}"


if __name__ == "__main__":
    sys.exit(1 if FAILURES else 0)
