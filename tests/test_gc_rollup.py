#!/usr/bin/env python3
"""Test `harness gc`'s cold-rollup path into memory/calibration/<month>.json.

The path had never produced a committed artifact (roadmap item 7,
proposals/2026-07-05-feature-improvement-roadmap.md): state/ is machine-local, so
no fresh clone can show the rollup working. This proves it against synthetic
state: cold scored records roll into the right monthly summary (n / scored /
hit_rate / brier), UNSCORED predictions never archive silently, hot records
stay, and a second batch MERGES into an existing month file instead of
clobbering it.

Stdlib only (CI runs `python3 tests/x.py`, no pip install).
Run:  python tests/test_gc_rollup.py

provenance: session 975732da, 2026-07-05 — roadmap item 7; the gc target
memory/calibration/*.json was empty in every checkout, leaving the rollup
path unproven.
"""
import datetime as dt
import importlib.machinery
import importlib.util
import json
import os
import tempfile
import types

def _repo_root():
    """Nearest ancestor holding bin/harness -- works from tests/ (final home) AND
    from the proposals/<bundle>/tests/ staging dir this ships in."""
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(d, "bin", "harness")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise SystemExit("FAIL: no repo root (bin/harness) above " + __file__)
        d = parent


ROOT = _repo_root()


def _load_harness_cli():
    """Import bin/harness (no .py extension) without running main() (guarded by
    __name__ == '__main__'); same pattern as tests/test_followup.py."""
    path = os.path.join(ROOT, "bin", "harness")
    loader = importlib.machinery.SourceFileLoader("harness_cli", path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("harness_cli", loader))
    loader.exec_module(mod)
    return mod


H = _load_harness_cli()
PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label}" + (f"  ({detail})" if detail else ""))


def iso(days_ago):
    t = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_ago)
    return t.isoformat(timespec="seconds")


def month_of(days_ago):
    t = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_ago)
    return t.strftime("%Y-%m")


# Redirect every ledger + the rollup target to a temp tree; the real state/ and
# memory/ are never touched.
tmp = tempfile.mkdtemp(prefix="gc_rollup_")
H.PREDICTIONS = os.path.join(tmp, "state", "predictions.jsonl")
H.CORRECTIONS = os.path.join(tmp, "state", "corrections.jsonl")
H.SKILL_USAGE = os.path.join(tmp, "state", "skill_usage.jsonl")
H.MEMORY = os.path.join(tmp, "memory")

os.makedirs(os.path.join(tmp, "state"))
for rec in (
    {"ts": iso(40), "id": "old-hit", "confidence": 0.8, "result": "hit"},
    {"ts": iso(40), "id": "old-miss", "confidence": 0.9, "result": "miss"},
    {"ts": iso(40), "id": "old-unscored", "confidence": 0.7, "result": None},
    {"ts": iso(1), "id": "recent-hit", "confidence": 0.6, "result": "hit"},
):
    with open(H.PREDICTIONS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
for rec in ({"ts": iso(40), "note": "old corr"}, {"ts": iso(1), "note": "new corr"}):
    with open(H.CORRECTIONS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
with open(H.SKILL_USAGE, "a", encoding="utf-8") as f:
    f.write(json.dumps({"ts": iso(40), "skill": "worktree", "session": "s"}) + "\n")

rc = H.cmd_gc(types.SimpleNamespace(days=30))
check("gc exits 0", rc == 0)

summary_path = os.path.join(H.MEMORY, "calibration", f"{month_of(40)}.json")
check("monthly summary created at memory/calibration/<month>.json",
      os.path.exists(summary_path), summary_path)
summary = json.load(open(summary_path, encoding="utf-8")) if os.path.exists(summary_path) else {}

pred = summary.get("predictions", {})
check("predictions bucket rolls the 2 scored cold records (n=2)", pred.get("n") == 2, pred)
check("scored count is 2", pred.get("scored") == 2, pred)
check("hit_rate is 0.5 (1 hit / 2 scored)", pred.get("hit_rate") == 0.5, pred)
check("brier recorded", isinstance(pred.get("brier"), float), pred)
check("corrections bucket n=1", summary.get("corrections", {}).get("n") == 1, summary)
check("skill_usage bucket n=1", summary.get("skill_usage", {}).get("n") == 1, summary)

hot = H._read(H.PREDICTIONS)
hot_ids = {r.get("id") for r in hot}
check("old UNSCORED prediction never archived silently", "old-unscored" in hot_ids, hot_ids)
check("recent prediction stays hot", "recent-hit" in hot_ids, hot_ids)
check("cold scored predictions left the hot ledger",
      not ({"old-hit", "old-miss"} & hot_ids), hot_ids)
check("recent correction stays hot", len(H._read(H.CORRECTIONS)) == 1)
check("cold skill_usage drained", len(H._read(H.SKILL_USAGE)) == 0)

# Second gc pass: nothing cold remains -> summary must NOT double-count.
H.cmd_gc(types.SimpleNamespace(days=30))
summary2 = json.load(open(summary_path, encoding="utf-8"))
check("re-running gc does not double-count", summary2.get("predictions", {}).get("n") == 2,
      summary2)

# A later cold batch MERGES into the existing month file (accumulate, not clobber).
with open(H.PREDICTIONS, "a", encoding="utf-8") as f:
    f.write(json.dumps({"ts": iso(40), "id": "old-hit-2", "confidence": 0.8,
                        "result": "hit"}) + "\n")
H.cmd_gc(types.SimpleNamespace(days=30))
summary3 = json.load(open(summary_path, encoding="utf-8"))
pred3 = summary3.get("predictions", {})
check("second batch accumulates n (2+1)", pred3.get("n") == 3, pred3)
check("hit_rate re-weighted ((1+1)/3 ~ 0.667)", pred3.get("hit_rate") == 0.667, pred3)

print(f"\n{PASS} passed, {FAIL} failed")
raise SystemExit(1 if FAIL else 0)
