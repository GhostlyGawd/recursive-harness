#!/usr/bin/env python3
"""Objective grader for cartograph-oracle.

Guards the PR #87 read-only agent surface of cartograph/extract.py — the
Structural Oracle (`--context`, `--query`) and Structural Reviewer (`--diff`).
argv[1] = sandbox dir (unused): like cartograph-extractor/gate this validates the
LIVE surface against the real harness repo, resolving the root from its own
location (evals/corpus/cartograph-oracle/check.py -> 4 dirs up).

These are COARSE CONTRACT assertions — valid --json shapes, a few anchor relations
that survive any honest refactor, exit codes, and read-only — NOT exact node/edge
counts. They are the regression-corpus floor (the only proof a later extractor
still answers correctly), deliberately complementary to test_query.py/test_diff.py,
which check the logic exhaustively. Floors are generous so honest harness growth
does not false-fail; only a wholesale break of the query surface trips it.

provenance: 2026-06-21, session f36989d6 — follow-up 540381 (eval guard for the
Bet A oracle + Bet B reviewer shipped in PR #87), routed via /harness-pr.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
extract = os.path.join(ROOT, "cartograph", "extract.py")
baseline = os.path.join(ROOT, "cartograph", "baseline.json")


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def run(*args):
    return subprocess.run([sys.executable, extract, *args],
                          capture_output=True, text=True)


def jrun(*args):
    r = run(*args)
    try:
        return r, json.loads(r.stdout)
    except json.JSONDecodeError:
        fail(f"`{' '.join(args)}` did not emit valid JSON: {(r.stdout + r.stderr)[-200:]}")


if not os.path.exists(extract):
    fail("cartograph/extract.py missing")
with open(baseline, "rb") as fh:
    bl_before = fh.read()

# --query blast-radius: transitive dependents, distance-tagged, non-empty for a hub
r, d = jrun("--query", "blast-radius", "skill:retrospection", "--json")
if r.returncode != 0:
    fail("blast-radius nonzero exit: " + r.stderr[-200:])
if not (d.get("kind") == "blast-radius" and d.get("target") == "skill:retrospection"
        and isinstance(d.get("result"), list)):
    fail("blast-radius json shape wrong: " + json.dumps(d)[:200])
if not (d["result"] and all("distance" in x and x["distance"] >= 1 for x in d["result"])):
    fail("blast-radius empty or missing distances (retrospection is a cited hub)")

# --query dependents anchor: settings.json wires the log_correction hook
r, d = jrun("--query", "dependents", "hook:log_correction", "--json")
if r.returncode != 0 or not isinstance(d.get("result"), list):
    fail("dependents shape/exit wrong: " + (r.stderr[-200:] or json.dumps(d)[:200]))
if not any(x["id"] == "config:settings.json" for x in d["result"]):
    fail("lost anchor: settings.json among log_correction's dependents")

# --query path anchor: /retro -> retro-miner (a known spawns edge)
r, d = jrun("--query", "path", "command:retro", "agent:retro-miner", "--json")
if r.returncode != 0:
    fail("path nonzero exit: " + r.stderr[-200:])
if not (d.get("path") and d["path"][0] == "command:retro"
        and d["path"][-1] == "agent:retro-miner" and d.get("length", 0) >= 1):
    fail("lost anchor: dependency path /retro -> retro-miner: " + json.dumps(d)[:200])

# --query orphans contract: a list, and config-type is EXCLUDED (verify-in-practice fix)
r, d = jrun("--query", "orphans", "--json")
if r.returncode != 0 or not isinstance(d.get("orphans"), list):
    fail("orphans shape/exit wrong: " + (r.stderr[-200:] or json.dumps(d)[:200]))
if any(o.get("type") == "config" for o in d["orphans"]):
    fail("orphans regressed: config-type nodes are runtime-read noise, must be excluded")

# --context brief: full shape + locked-layer flag for a hooks/ file
r, d = jrun("--context", "hooks/log_correction.py", "--json")
if r.returncode != 0:
    fail("context nonzero exit: " + r.stderr[-200:])
need = ("node", "provenance", "dependencies", "dependents", "blast_radius", "flags")
if not (all(k in d for k in need) and d["node"].get("type") == "hook"):
    fail("context brief missing keys or wrong node type: " + json.dumps(d)[:200])
if d["flags"].get("locked_layer") is not True:
    fail("context flags.locked_layer must be True for a hooks/ file")

# resolution failure: non-zero, one-liner, NEVER a traceback
r = run("--context", "does/not/exist_xyz.py")
if r.returncode == 0:
    fail("bogus --context unexpectedly exited 0")
if "Traceback" in (r.stdout + r.stderr):
    fail("bogus --context leaked a traceback (must be a clean one-line error)")

# --diff self-diff: advisory exit 0 + verdict clean AND a truly empty raw delta.
# PR #91 made the --diff CURRENT side tracked-only (it compares git-tracked files
# vs the git REF, ignoring gitignored on-disk artifacts like skills/brand-foundry),
# so a tree diffed against itself now adds nothing — zero nodes, zero edges.
r, d = jrun("--diff", "HEAD", "--json")
if r.returncode != 0:
    fail("--diff HEAD (advisory) did not exit 0: " + r.stderr[-200:])
if d.get("verdict", {}).get("clean") is not True:
    fail("self-diff verdict not clean (no rot/review finding should arise diffing a tree against itself)")
if d.get("nodes_added") or d.get("edges_added"):
    fail("self-diff added nodes/edges (tracked-only current side must add nothing vs itself): " + json.dumps(d)[:200])
if run("--diff", "HEAD", "--strict").returncode != 0:
    fail("--diff HEAD --strict exited nonzero (self-diff has zero blocking findings)")

# read-only floor: the whole query surface must not mutate the committed baseline
with open(baseline, "rb") as fh:
    if fh.read() != bl_before:
        fail("baseline.json changed — the oracle/reviewer surface must be read-only")

print("ok (query/context/diff contracts + 3 anchors hold, orphans excludes config, "
      "self-diff clean, read-only)")
sys.exit(0)
