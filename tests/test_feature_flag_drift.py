#!/usr/bin/env python3
"""Anti-drift test for the DELIBERATE feature-flag duplication between
hooks/harness_features.py (the hooks' reader) and bin/harness (inline mirror —
bin/ is intentionally off the hooks/ import path; both files flag the risk
in-code). If the two LOCKED sets or reader semantics ever diverge, an agent
could flip via `harness features set` a key the hooks still treat as
guard-weakening (or vice versa). This pins:

1. The LOCKED key sets are identical.
2. Reader parity on the same fixture: LOCKED keys ignore the local override in
   BOTH readers; SOFT keys honor local > committed > caller default in BOTH.

Stdlib only (CI runs `python3 tests/x.py`, no pip install).
Run:  python tests/test_feature_flag_drift.py

provenance: session 975732da, 2026-07-05 — roadmap item 8
(proposals/resolved/P-2026-038-feature-improvement-roadmap.md); the drift risk is
documented in both files but was enforced by nothing.
"""
import importlib.machinery
import importlib.util
import json
import os
import tempfile

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


def _load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, path)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(mod)
    return mod


CLI = _load("harness_cli", os.path.join(ROOT, "bin", "harness"))
HF = _load("harness_features_mod", os.path.join(ROOT, "hooks", "harness_features.py"))

PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label}" + (f"  ({detail})" if detail else ""))


# --- 1. the two LOCKED sets are byte-identical -------------------------------
check("LOCKED sets identical (hooks vs CLI mirror)",
      set(HF.LOCKED) == set(CLI.LOCKED_FEATURES),
      f"only-hooks={set(HF.LOCKED) - set(CLI.LOCKED_FEATURES)} "
      f"only-cli={set(CLI.LOCKED_FEATURES) - set(HF.LOCKED)}")

# --- 2. reader parity on one shared fixture ----------------------------------
tmp = tempfile.mkdtemp(prefix="flagdrift_")
committed = os.path.join(tmp, "features.json")
local = os.path.join(tmp, "features.local.json")
with open(committed, "w", encoding="utf-8") as f:
    json.dump({"guards": {"worktree_session": {"block": True, "ttl_seconds": 900}},
               "observability": {"log_skill_use": True}}, f)
with open(local, "w", encoding="utf-8") as f:
    json.dump({"guards.worktree_session.block": False,       # LOCKED: must be IGNORED
               "guards.worktree_session.ttl_seconds": 5,     # LOCKED: must be IGNORED
               "observability.log_skill_use": False,         # SOFT: must override
               "workflow.only_local_key": 7}, f)              # SOFT, local-only

# Point both readers at the same fixture (both expose monkeypatchable globals).
HF.FEATURES_PATH, HF.LOCAL_PATH = committed, local
CLI.FEATURES, CLI.FEATURES_LOCAL = committed, local

PROBES = [
    ("guards.worktree_session.block", None),
    ("guards.worktree_session.ttl_seconds", None),
    ("observability.log_skill_use", None),
    ("workflow.only_local_key", None),
    ("missing.key.entirely", "caller-default"),
]
for key, default in PROBES:
    hv, cv = HF.flag(key, default), CLI._feature(key, default)
    check(f"parity: {key} -> {hv!r}", hv == cv, f"hooks={hv!r} cli={cv!r}")

check("LOCKED key ignores local override (both readers)",
      HF.flag("guards.worktree_session.block", None) is True)
check("LOCKED ttl ignores local override (both readers)",
      HF.flag("guards.worktree_session.ttl_seconds", None) == 900)
check("SOFT key honors local override (both readers)",
      HF.flag("observability.log_skill_use", None) is False)
check("missing key falls back to caller default (both readers)",
      HF.flag("missing.key.entirely", "caller-default") == "caller-default")

print(f"\n{PASS} passed, {FAIL} failed")
raise SystemExit(1 if FAIL else 0)
