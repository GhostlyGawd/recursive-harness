#!/usr/bin/env python3
"""Objective grader for cartograph-audit.

Guards the autophagic self-audit feed of cartograph/extract.py — `--audit`
(advisory candidates for /meta-retro: structural rot + dead weight). argv[1] =
sandbox dir (unused): like the sibling cartograph cases this validates the LIVE
feed against the real harness repo, resolving the root from its own location
(evals/corpus/cartograph-audit/check.py -> 4 dirs up).

Coarse CONTRACT assertions: the JSON shape, the invariants that the audit is
advisory + read-only (`meta.mutates is False`) and that its rot set AGREES with
the gate (`--check`) — not exact candidate lists. test_audit.py checks the
logic; this is the regression-corpus floor.

provenance: 2026-06-21, session f36989d6 — follow-up 99ee20 (eval guard for
--audit, mirroring cartograph-extractor/gate), routed via /harness-pr.
"""
import json
import os
import subprocess
import sys
import tempfile

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


if not os.path.exists(extract):
    fail("cartograph/extract.py missing")
with open(baseline, "rb") as fh:
    bl_before = fh.read()

# 1. human form runs clean and is self-labelled as the advisory audit
r = run("--audit")
if r.returncode != 0:
    fail("--audit (human) nonzero exit: " + r.stderr[-200:])
if "SELF-AUDIT" not in r.stdout:
    fail("--audit human output is not the self-audit report")

# 2. JSON form (written to a path) has the documented shape
with tempfile.TemporaryDirectory() as d:
    out = os.path.join(d, "audit.json")
    r = run("--audit", out)
    if r.returncode != 0:
        fail("--audit <path> nonzero exit: " + r.stderr[-200:])
    try:
        a = json.load(open(out, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail("audit json unreadable: " + str(e))

for k in ("structural_rot", "dead_weight", "meta"):
    if k not in a:
        fail(f"audit json missing top-level key '{k}'")
for k in ("advisory", "mutates", "rot_count", "dead_weight_count"):
    if k not in a["meta"]:
        fail(f"audit meta missing key '{k}'")

# 3. load-bearing invariants: advisory + READ-ONLY (never auto-acts/mutates)
if a["meta"].get("advisory") is not True:
    fail("audit must be advisory (meta.advisory != True)")
if a["meta"].get("mutates") is not False:
    fail("audit must be read-only (meta.mutates != False) — it never prunes, the human decides")

# 4. counts are self-consistent with their lists
if len(a["structural_rot"]) != a["meta"]["rot_count"]:
    fail("meta.rot_count disagrees with len(structural_rot)")
if len(a["dead_weight"]) != a["meta"]["dead_weight_count"]:
    fail("meta.dead_weight_count disagrees with len(dead_weight)")

# 5. cross-consistency anchor: the audit's rot is the SAME set the gate blocks on,
#    so a clean gate (--check exit 0) implies zero audit rot, and vice-versa.
gate_clean = run("--check").returncode == 0
if (a["meta"]["rot_count"] == 0) != gate_clean:
    fail(f"audit rot ({a['meta']['rot_count']}) and gate (clean={gate_clean}) disagree on structural rot")

# 6. read-only floor
with open(baseline, "rb") as fh:
    if fh.read() != bl_before:
        fail("baseline.json changed — --audit must be read-only")

print(f"ok (shape valid, advisory + read-only, counts consistent, "
      f"rot agrees with gate [rot={a['meta']['rot_count']}, gate_clean={gate_clean}])")
sys.exit(0)
