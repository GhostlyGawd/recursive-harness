#!/usr/bin/env python3
"""Objective grader for mission-control-p2p5.

argv[1] = sandbox dir (unused). Like cartograph-gate, this case validates the LIVE Mission
Control artifacts against the real harness repo, so it resolves the repo root from its own
location. It walks UP to the dir that holds BOTH cartograph/extract.py and mission_control/ —
so it is valid both at evals/corpus/mission-control-p2p5/check.py (post-merge, 4 dirs up) AND
at proposals/resolved/P-2026-015-mission-control-gated-bundle/eval/check.py (pre-merge staging).

Headless by contract: no real terminal, no textual widget pilot (the widget behaviour lives in
mission_control/test_*.py). Asserts the four load-bearing P2-P5 invariants — see task.md.
"""
import json
import os
import subprocess
import sys


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def find_root(start):
    """Walk up from `start` to the dir holding both cartograph/extract.py and mission_control/."""
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, "cartograph", "extract.py")) and os.path.isdir(
            os.path.join(d, "mission_control")
        ):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


ROOT = find_root(os.path.dirname(os.path.abspath(__file__)))
if not ROOT:
    fail("could not locate the harness repo root (cartograph/extract.py + mission_control/)")


def _require(d, *keys):
    """Assert nested keys exist in dict `d` (None values are allowed — the honesty contract;
    a MISSING key would crash the TUI's `.get(...)` chain, a None degrades to a dash)."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            fail(f"--mission payload missing key path: {'.'.join(keys)} (stopped at {k!r})")
        cur = cur[k]


# ── 1. P0 data contract: extract.py --mission emits what mission_control/data.py binds to ──────
extract = os.path.join(ROOT, "cartograph", "extract.py")
proc = subprocess.run(
    [sys.executable, extract, "--mission", "--quiet"],
    capture_output=True, text=True, cwd=ROOT, timeout=120,
)
if proc.returncode != 0:
    fail(f"extract.py --mission exited {proc.returncode}: {(proc.stderr or '')[-300:]}")
try:
    payload = json.loads(proc.stdout)
except json.JSONDecodeError as e:
    fail(f"--mission did not emit valid JSON: {e}")

_require(payload, "structure", "node_count")
_require(payload, "structure", "edge_count")
_require(payload, "structure", "nodes")
_require(payload, "structure", "edges")
_require(payload, "work", "by_component")
_require(payload, "work", "in_flight")
_require(payload, "work", "followups_open")
_require(payload, "health", "predictions", "hit_rate")
_require(payload, "health", "predictions", "total")
_require(payload, "health", "predictions", "unscored")
_require(payload, "health", "corrections_total")
_require(payload, "health", "eval_cases", "present")
_require(payload, "health", "eval_cases", "total")
_require(payload, "health", "structural_rot")
if not isinstance(payload["structure"]["nodes"], list):
    fail("structure.nodes is not a list")

# ── 2. P1 firewall: the data/feed layer imports with textual unimportable ───────────────────────
firewall = (
    "import sys; sys.modules['textual'] = None\n"   # any `import textual` now raises ImportError
    "import mission_control.data, mission_control.feed\n"
    "print('ok')\n"
)
env = dict(os.environ, PYTHONPATH=ROOT)
fw = subprocess.run([sys.executable, "-c", firewall], capture_output=True, text=True,
                    cwd=ROOT, env=env, timeout=60)
if fw.returncode != 0:
    fail("data/feed do not import without textual (firewall breach): "
         + (fw.stderr or fw.stdout)[-300:])

# ── 3. P4 live-feed lifecycle (read-only) ───────────────────────────────────────────────────────
sys.path.insert(0, ROOT)
try:
    from fleet import eventlog as el
except ImportError as e:
    fail(f"fleet.eventlog unavailable: {e}")

now = 1_000_000.0
events = [
    el.new_event("note", actor="a", ttl_s=10, now_s=now - 100),   # past-TTL -> reaped
    el.new_event("note", actor="b", ttl_s=10_000, now_s=now - 1),  # live     -> kept
]
live = el.reap(events, now_s=now)
if len(live) != 1 or live[0]["actor"] != "b":
    fail(f"reap did not drop the past-TTL event (kept {[e['actor'] for e in live]})")

feed = el.live_feed(
    [el.new_event("note", actor="x", ttl_s=10_000, now_s=now - 5),
     el.new_event("note", actor="y", ttl_s=10_000, now_s=now - 1)],
    now_s=now, window_s=900,
)
if [e["actor"] for e in feed] != ["y", "x"]:
    fail(f"live_feed is not newest-first: {[e['actor'] for e in feed]}")

import tempfile
with tempfile.TemporaryDirectory() as d:
    if el.read_feed(d, now_s=now) != []:
        fail("read_feed on an absent log did not return []")
    if os.path.exists(os.path.join(d, "fleet", "events.jsonl")):
        fail("read_feed CREATED the event log (must be read-only)")

# ── 4. P5 anti-scratchpad guard: block a new scratchpad, stay silent otherwise ──────────────────
guard = os.path.join(ROOT, "hooks", "forbid_scratchpad.py")
if not os.path.exists(guard):  # pre-merge: the staged copy
    guard = os.path.join(ROOT, "proposals", "2026-06-23-mission-control-p5-guard",
                         "forbid_scratchpad.py")
if not os.path.exists(guard):
    fail("forbid_scratchpad.py not found in hooks/ or the staging proposal dir")

# the guard's repo scope is dirname(dirname(guard)); put test paths under it so the block fires
# whether the guard lives in hooks/ (scope=repo root) or proposals/<dir>/ (scope=proposals/).
guard_root = os.path.dirname(os.path.dirname(guard))
state_md = os.path.join(guard_root, "STATE.md")
readme_md = os.path.join(guard_root, "README_eval_probe.md")


def run_guard(event):
    return subprocess.run([sys.executable, guard], input=json.dumps(event),
                          capture_output=True, text=True, timeout=30).returncode


cases = [
    ("block new STATE.md (Write)", 2,
     {"tool_name": "Write", "tool_input": {"file_path": state_md}}),
    ("block STATE.md via Bash tee", 2,
     {"tool_name": "Bash", "tool_input": {"command": f"echo x | tee {state_md}"}}),
    ("allow a normal new file (Write)", 0,
     {"tool_name": "Write", "tool_input": {"file_path": readme_md}}),
    ("allow Edit of STATE.md (cannot create)", 0,
     {"tool_name": "Edit", "tool_input": {"file_path": state_md}}),
    ("allow Bash read of STATE.md", 0,
     {"tool_name": "Bash", "tool_input": {"command": f"cat {state_md}"}}),
]
for label, want, event in cases:
    got = run_guard(event)
    if got != want:
        fail(f"guard: {label} -> exit {got}, want {want}")

print("ok (--mission contract intact; firewall holds; feed reaps + read-only; guard blocks "
      "new scratchpads only)")
sys.exit(0)
