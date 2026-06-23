#!/usr/bin/env python3
"""Tests for Mission Control P4 - the live-feed (Terminal) lens, coupled READ-ONLY to the existing
fleet.eventlog substrate. The emit/act + reaper + bin subcommand are GATED (staged as a /harness-pr);
this lens only READS.

Two tiers:
  [1] data firewall - pure logic + the fleet engine, runs WITHOUT textual. UNIT + PROPERTY.
  [2] textual pilot - the Console lens shows a Terminal panel rendering the live feed (newest-first);
      an absent log degrades to an empty ticker, never a crash.

P4 SUCCESS CRITERIA (inline; no governing spec):

  C1 RESOLVE THE CANONICAL STATE DIR. `resolve_state_dir(root=X)` -> X/state (the path the TUI's
     --root supplies). With no root it mirrors `git rev-parse --git-common-dir` to the MAIN
     checkout's state/ - so the feed read from a WORKTREE sees the shared log, not the worktree's
     gitignored-empty tree-local one. git absent/error -> falls back to <start>/state; never raises.
  C2 READ-ONLY, ZERO WRITES. `read_events` reads through `fleet.read_feed` and writes NOTHING:
     repeated reads leave the log file + its directory byte-for-byte unchanged and create no new
     file. (The act/emit half is gated; the lens only reads - the prediction's read-only claim.)
  C3 FAITHFUL, BOUNDED FOLD. `to_feed_lines(events)` folds each event to one FeedLine preserving
     fleet's order (newest-first), no drop / no add, with bounded fields (actor truncated, payload
     summarised - no free-prose dump). Empty/absent -> [].
  C4 WINDOW + EXCLUDE PASS-THROUGH. `read_events` forwards window_s + exclude_actor to the engine, so
     the lens shows a recent window and can hide your own actor - it AGREES with fleet.read_feed.
  C5 TERMINAL LENS (behavioural). The Console lens shows a Terminal panel rendering the feed
     newest-first; an absent feed degrades to an empty ticker, never a crash.

Run:  python mission_control/test_feed.py
"""
import os
import random
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from fleet import eventlog as el
from mission_control import feed

_passed = 0
_failed = 0


def check(cond, label):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}")


def _git(args, cwd):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t", PYTHONUTF8="1")
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)


# ════════════════════════════════════════════════════════════ [1a] resolve_state_dir (C1)
def test_resolve_root():
    print("[1a] resolve_state_dir: --root -> <root>/state; non-git -> fallback; never raises (C1)")
    check(feed.resolve_state_dir(root="/x/y") == os.path.join("/x/y", "state"),
          "an explicit --root resolves to <root>/state")
    with tempfile.TemporaryDirectory() as nongit:
        got = feed.resolve_state_dir(start=nongit)
        check(got == os.path.join(nongit, "state"),
              "a non-git start dir falls back to <start>/state (no raise)")


def test_resolve_worktree_canonical():
    print("[1b] resolve_state_dir from a WORKTREE points at the MAIN checkout's state (C1)")
    with tempfile.TemporaryDirectory() as base:
        main = os.path.join(base, "main")
        os.makedirs(main)
        open(os.path.join(main, "seed.txt"), "w").close()
        _git(["init", "-q"], main)
        _git(["add", "-A"], main)
        _git(["commit", "-q", "-m", "seed"], main)
        wt = os.path.join(base, "wt")
        _git(["worktree", "add", "-q", wt, "-b", "wtb"], main)
        main_state = os.path.realpath(os.path.join(main, "state"))
        got = os.path.realpath(feed.resolve_state_dir(start=wt))
        check(got == main_state,
              "resolver(worktree) -> MAIN/state (the feed reads the shared log, not the empty wt one)")


# ════════════════════════════════════════════════════════════ [1c] read_events: read-only (C2)
def test_read_only_zero_writes():
    print("[1c] read_events is READ-ONLY: repeated reads write nothing, do NOT reap/compact (C2)")
    d = tempfile.mkdtemp()
    try:
        # one LIVE record + one EXPIRED record. A secretly-writing adapter (e.g. one that calls
        # compact()/reap-to-disk on every read) would DROP the expired record and change the bytes.
        # Read-only must leave BOTH on disk, byte-for-byte, mtime untouched. (Closes the compact hole.)
        el.emit(d, "progress", payload={"branch": "feat/x"}, ttl_s=10_000, now_s=1000.0)
        el.emit(d, "note", payload={}, ttl_s=10, now_s=100.0)   # expires at 110, dead at now=2000
        fdir = os.path.join(d, "fleet")
        path = os.path.join(fdir, "events.jsonl")
        before = open(path, encoding="utf-8").read()
        before_ls = sorted(os.listdir(fdir))
        before_mtime = os.stat(path).st_mtime_ns
        for _ in range(3):
            feed.read_events(d, now_s=2000.0, window_s=100_000)
        check(open(path, encoding="utf-8").read() == before, "the log file is byte-for-byte unchanged")
        check(os.stat(path).st_mtime_ns == before_mtime, "the log mtime is unchanged (no rewrite/compact)")
        check(sorted(os.listdir(fdir)) == before_ls, "no new file is created by reading (e.g. no .tmp)")
        check(len(el.read_raw(d)) == 2,
              "the EXPIRED record still on disk after reads - read did not reap/compact (zero writes)")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_read_absent_log():
    print("[1d] read_events on an absent log -> [] (degrade, never crash) (C3/C5)")
    d = tempfile.mkdtemp()
    try:
        check(feed.read_events(d, now_s=1000.0) == [], "absent fleet log -> empty list")
        check(feed.to_feed_lines([]) == [], "empty events -> no feed lines")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_resolve_git_error_fallback():
    print("[1d2] resolve_state_dir: a git error/non-zero -> fallback to <start>/state, never raises (C1)")
    orig = feed.subprocess.run
    with tempfile.TemporaryDirectory() as d:
        try:
            feed.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(OSError("git boom"))
            check(feed.resolve_state_dir(start=d) == os.path.join(d, "state"),
                  "a RAISING git call falls back to <start>/state (no crash)")

            class _R:
                returncode = 1
                stdout = ""
                stderr = "fatal"
            feed.subprocess.run = lambda *a, **k: _R()
            check(feed.resolve_state_dir(start=d) == os.path.join(d, "state"),
                  "a NON-ZERO git exit falls back to <start>/state")
        finally:
            feed.subprocess.run = orig


def test_composed_loader_canonical():
    print("[1d3] make_loader composes resolve+read: from a WORKTREE it reads MAIN's log, not wt's (C1)")
    with tempfile.TemporaryDirectory() as base:
        main = os.path.join(base, "main")
        os.makedirs(main)
        open(os.path.join(main, "seed.txt"), "w").close()
        _git(["init", "-q"], main)
        _git(["add", "-A"], main)
        _git(["commit", "-q", "-m", "seed"], main)
        wt = os.path.join(base, "wt")
        _git(["worktree", "add", "-q", wt, "-b", "wtb"], main)
        # emit into MAIN's state (the shared, canonical log)
        el.emit(os.path.join(main, "state"), "progress", payload={"branch": "feat/z"},
                ttl_s=10_000, now_s=1000.0)
        loader = feed.make_loader(start=wt, now_s=1001.0, window_s=10_000)
        evts = loader()
        check(any((e.get("payload") or {}).get("branch") == "feat/z" for e in evts),
              "the composed loader read MAIN/state from the worktree (resolve->read seam wired)")


# ════════════════════════════════════════════════════════════ [1e] to_feed_lines fold (C3)
def test_fold_units():
    print("[1e] to_feed_lines: faithful, bounded, order-preserving fold (C3)")
    events = [
        {"id": "a", "ts": 970.0, "actor": "abcdefghijКЛМ", "kind": "progress",
         "target": "", "payload": {"branch": "feat/x", "pct": 40}},
        {"id": "b", "ts": 920.0, "actor": "you", "kind": "claim",
         "target": "src/**", "payload": {}},
    ]
    lines = feed.to_feed_lines(events)
    check(len(lines) == 2, "one feed line per event (no drop, no add)")
    check([l.ts for l in lines] == [970.0, 920.0], "fold PRESERVES fleet's order (newest-first)")
    check(lines[0].kind == "progress" and lines[1].kind == "claim", "kind carried through")
    check(lines[1].target == "src/**", "target carried through")
    check(len(lines[0].actor) <= 8, "actor is bounded (truncated), not dumped whole")
    check("feat/x" in lines[0].text, "payload is summarised into the line text")
    check(all(l.text is not None for l in lines), "no None field leaks into a line")


# ════════════════════════════════════════════════════════════ [1f] window/exclude pass-through (C4)
def test_window_exclude_passthrough():
    print("[1f] read_events forwards window_s + exclude_actor; agrees with fleet.read_feed (C4)")
    d = tempfile.mkdtemp()
    try:
        el.emit(d, "note", payload={}, ttl_s=10_000, now_s=850.0, actor="old")
        el.emit(d, "note", payload={}, ttl_s=10_000, now_s=960.0, actor="me")
        el.emit(d, "note", payload={}, ttl_s=10_000, now_s=970.0, actor="you")
        # window of 100 from now=1000 excludes the ts=850 event
        got = feed.read_events(d, now_s=1000.0, window_s=100.0)
        oracle = el.read_feed(d, now_s=1000.0, window_s=100.0)
        check([e["ts"] for e in got] == [e["ts"] for e in oracle] == [970.0, 960.0],
              "window_s forwarded: read_events agrees with the engine projection")
        got2 = feed.read_events(d, now_s=1000.0, window_s=100.0, exclude_actor="me")
        check([e["actor"] for e in got2] == ["you"], "exclude_actor forwarded: own actor hidden")
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ════════════════════════════════════════════════════════════════════════ [1p] PROPERTY tests
def _rand_events(rng):
    n = rng.randint(0, 20)
    kinds = ["progress", "claim", "release", "note", "handoff"]
    out = []
    for i in range(n):
        out.append({
            "id": f"{i:012x}", "ts": float(1000 - i),  # already newest-first
            "actor": "".join(rng.choice("abcdef0123") for _ in range(rng.randint(1, 16))),
            "kind": rng.choice(kinds),
            "target": rng.choice(["", "src/**", "branch:x", None]),
            "payload": {"k": rng.randint(0, 9)} if rng.random() < 0.7 else {},
        })
    return out


def test_properties():
    print("[1p] properties over 300 randomized event lists (fold invariants)")
    rng = random.Random(20260623)
    bad_len = bad_order = bad_bound = bad_none = 0
    for _ in range(300):
        ev = _rand_events(rng)
        lines = feed.to_feed_lines(ev)
        if len(lines) != len(ev):                       # conservation: no drop / no add
            bad_len += 1
        if [l.ts for l in lines] != [e["ts"] for e in ev]:   # order preserved
            bad_order += 1
        for l in lines:
            if len(l.actor) > 8:                        # bounded actor
                bad_bound += 1
            if l.kind is None or l.target is None or l.text is None:  # no None leak
                bad_none += 1
    check(bad_len == 0, "P-C3a one line per event on every list (conservation)")
    check(bad_order == 0, "P-C3b fold preserves the engine's newest-first order")
    check(bad_bound == 0, "P-C3c actor is always bounded to <=8 chars")
    check(bad_none == 0, "P-C3d no None leaks into kind/target/text")


# ═══════════════════════════════════════════════════════════════════ [2] textual pilot (C5)
async def _pilot():
    from textual.widgets import Static
    from mission_control.app import MissionControl

    # minimal payload so the console lens has lanes + proof; feed injected separately
    payload = {
        "structure": {"nodes": [{"id": "skill:a", "type": "skill", "label": "a", "loop": "core",
                                 "file": "skills/a/SKILL.md"}], "edges": [], "node_count": 1, "edge_count": 0},
        "work": {"by_component": {"skill:a": {"component": {"id": "skill:a", "type": "skill",
                 "file": "skills/a/SKILL.md"}, "followups": [{"id": "x", "text": "open", "task": "", "ts": 1}]}},
                 "unscoped": {"followups": []}, "proposals": [], "followups_open": 1, "in_flight": {}},
        "health": {}, "meta": {"view": "mission"},
    }
    events = [
        {"id": "a", "ts": 970.0, "actor": "peer1", "kind": "progress",
         "target": "branch:feat/x", "payload": {"branch": "feat/x"}},
        {"id": "b", "ts": 920.0, "actor": "peer2", "kind": "claim",
         "target": "src/**", "payload": {}},
    ]
    app = MissionControl(lambda: payload, feed_loader=lambda: events,
                         name_label="MISSION CONTROL", channel="01")
    async with app.run_test() as pilot:
        await pilot.pause()
        while app.lens != "console":
            await pilot.press("tab")
            await pilot.pause()
        term = app.query_one("#terminal", Static)
        check(term.display, "the Terminal panel is visible in the Console lens")
        txt = str(term.render())
        check("progress" in txt and "claim" in txt, "the Terminal renders the live feed events")
        check(txt.index("progress") < txt.index("claim"),
              "the feed is newest-first (the ts=970 progress above the ts=920 claim)")

    # absent feed degrades to an empty ticker, no crash
    app2 = MissionControl(lambda: payload, feed_loader=lambda: [],
                          name_label="MISSION CONTROL", channel="01")
    async with app2.run_test() as pilot:
        await pilot.pause()
        while app2.lens != "console":
            await pilot.press("tab")
            await pilot.pause()
        term2 = app2.query_one("#terminal", Static)
        check(term2.display, "Terminal panel still present with an empty feed")
        check("—" in str(term2.render()) or str(term2.render()).strip() != "",
              "an empty feed renders an idle ticker, not a crash")


def test_tui():
    print("[2] textual pilot: Terminal lens renders the live feed newest-first (C5)")
    try:
        import textual  # noqa: F401
    except ImportError:
        print("  skip (textual not installed)")
        return
    import asyncio
    asyncio.run(_pilot())


if __name__ == "__main__":
    for fn in (test_resolve_root, test_resolve_worktree_canonical, test_read_only_zero_writes,
               test_read_absent_log, test_resolve_git_error_fallback, test_composed_loader_canonical,
               test_fold_units, test_window_exclude_passthrough, test_properties, test_tui):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _failed += 1
            print(f"  FAIL {fn.__name__} raised {type(exc).__name__}: {exc}")
    print(f"\n{_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)
