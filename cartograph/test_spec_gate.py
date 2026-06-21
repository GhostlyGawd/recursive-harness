#!/usr/bin/env python3
"""Red-first tests for Spec-Driven Development Phase B (the spec-binding gate classes).

Authoritative spec: proposals/2026-06-21-spec-driven-dev.md, Decision E + the build-phasing
table (Phase B). Every check below is derived from an INTENT clause in that proposal, NOT
from the extract.py code it drives. Phase A (test_spec.py) proved the spec EDGES are drawn and
that an absent pointer draws an edge to a missing=True node WITHOUT warning; Phase B is the
warn() layer that turns those missing endpoints into gateable rot:

  * Decision E (a) - `dangling-spec:<slug>:<pointer>`: a targets:/verified_by: pointer (spec OR
    requirement altitude) that resolves to a missing node is dangling rot - the direct mirror of
    `dangling-adr`. It ALWAYS fires, independent of status: (status cannot suppress it). Keyed
    per (spec-slug, pointer) so each dangling pointer grandfathers/clears independently.
  * Decision E (b) - `untested-requirement:<slug>/<rid>`: the EARS teeth. An EARS requirement
    carrying NO verified_by edge to a REAL (non-missing) eval-corpus case. It fires ONLY when its
    governing spec is `status: shipped` (the chosen strictness threshold; proposed/building defer
    it). A requirement whose only verified_by is dangling is therefore BOTH dangling-spec (the
    pointer) AND untested-requirement (no real verification) at shipped.
  * ANTI-BACKDOOR INVARIANT - status: is descriptive and may only ratchet strictness UP. No
    status value can SKIP a check: `proposed` defers ONLY untested-requirement; dangling-spec
    still fires. status: is never trusted as proof of verification - proof is a resolved edge to
    a real eval node, asserted against machine truth (filesystem existence).
  * Trunk dormancy / count-neutrality - a no-binding fixture and a fully-resolving shipped
    fixture each produce ZERO spec warnings, so the (binding-free) trunk gate stays clean and
    baseline.json is untouched. Phase B is inert until a real binding is authored.
  * Gate integration - a dangling-spec fingerprint flows through gate()/--check exactly like
    orphan-hook/dangling-adr: NEW under an empty baseline (blocks), grandfathered once baselined.

Same runner style as test_spec.py: pure-logic units build the graph in-process on throwaway
--root fixtures; e2e cases drive the CLI so the real trunk stays count-neutral.

Run:  python cartograph/test_spec_gate.py      # exits non-zero on any failure
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, "extract.py")

_spec = importlib.util.spec_from_file_location("cartograph_extract", EXTRACT)
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)

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


def run(*args):
    r = subprocess.run([sys.executable, EXTRACT, *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def build_at(d):
    """Build the graph for a throwaway root in-process, returning (graph, warnings)."""
    old = ex.ROOT
    try:
        ex.ROOT = os.path.abspath(d)
        g, warnings, notes, wired = ex.build()
    finally:
        ex.ROOT = old
    return g, warnings


def fps(warnings):
    return {w["fingerprint"] for w in warnings}


def minimal_root(d):
    """The two files build() always needs so it does not choke on a bare root."""
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "CLAUDE.md"), "# kernel\n")


def binding_skill(d, name, slug, status, targets, spec_vbs, reqs):
    """Lay down skills/<name>/SKILL.md carrying a spec binding. `reqs` is a list of
    (rid, [verified_by...]) tuples. Pointers are written verbatim - the caller decides which
    resolve (create the target/eval on disk) and which dangle (omit it)."""
    tline = "targets: [" + ", ".join(targets) + "]\n" if targets else ""
    vline = "verified_by: [" + ", ".join(spec_vbs) + "]\n" if spec_vbs else ""
    rblock = ""
    if reqs:
        rblock = "requirements:\n"
        for rid, vbs in reqs:
            rblock += f"  - id: {rid}\n"
            rblock += f'    ears: "WHEN x, THE SYSTEM SHALL y ({rid})"\n'
            if vbs:
                rblock += "    verified_by: [" + ", ".join(vbs) + "]\n"
    fm = (f"---\nname: {name}\nspec: {slug}\n"
          f"intent: phase B gate fixture\n{tline}{vline}status: {status}\n{rblock}---\nbody.\n")
    write(os.path.join(d, "skills", name, "SKILL.md"), fm)


def make_eval(d, slug):
    write(os.path.join(d, "evals", "corpus", slug, "task.md"), f"# {slug}\n")


# ============================================================ 1. dangling targets: pointer
print("[1] a targets: pointer to a non-existent file fires dangling-spec (ALWAYS, mirror of dangling-adr)")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    # governs itself (resolves) + a ghost file that does NOT exist on disk (dangles)
    binding_skill(d, "gov1", "spec-one", "building",
                  targets=["skills/gov1/SKILL.md", "skills/ghost/SKILL.md"],
                  spec_vbs=[], reqs=[])
    g, warnings = build_at(d)
    f = fps(warnings)
    want = "dangling-spec:spec-one:skills/ghost/SKILL.md"
    check(want in f, f"dangling targets pointer -> exact fingerprint {want!r} (got spec fps "
                     f"{sorted(x for x in f if x.startswith('dangling-spec'))})")
    check(not any(x == "dangling-spec:spec-one:skills/gov1/SKILL.md" for x in f),
          "the RESOLVING targets pointer (self) produces NO dangling-spec warning")


# ============================================================ 2. dangling verified_by (spec altitude)
print("[2] a spec-altitude verified_by pointer to a missing eval-case fires dangling-spec")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    make_eval(d, "real-eval")   # one resolves
    binding_skill(d, "gov2", "spec-two", "proposed",
                  targets=["skills/gov2/SKILL.md"],
                  spec_vbs=["evals/corpus/real-eval", "evals/corpus/ghost-eval"], reqs=[])
    g, warnings = build_at(d)
    f = fps(warnings)
    want = "dangling-spec:spec-two:evals/corpus/ghost-eval"
    check(want in f, f"dangling spec-altitude verified_by -> {want!r}")
    check("dangling-spec:spec-two:evals/corpus/real-eval" not in f,
          "the RESOLVING verified_by pointer (real-eval exists) produces NO dangling-spec")


# ============================================================ 3. dangling requirement-altitude verified_by
print("[3] a requirement-altitude verified_by to a missing eval fires dangling-spec AND (shipped) untested")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    binding_skill(d, "gov3", "spec-three", "shipped",
                  targets=["skills/gov3/SKILL.md"], spec_vbs=[],
                  reqs=[("R1", ["evals/corpus/missing-eval"])])
    g, warnings = build_at(d)
    f = fps(warnings)
    check("dangling-spec:spec-three:evals/corpus/missing-eval" in f,
          "a requirement's dangling verified_by fires dangling-spec keyed by the SPEC slug")
    # the requirement has NO edge to a REAL eval, and the spec is shipped -> ALSO untested
    check("untested-requirement:spec-three/R1" in f,
          "a shipped requirement whose only verified_by dangles is BOTH dangling AND untested")


# ============================================================ 4. untested-requirement (shipped, empty verified_by)
print("[4] a SHIPPED spec's requirement with NO verified_by at all fires untested-requirement")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    binding_skill(d, "gov4", "spec-four", "shipped",
                  targets=["skills/gov4/SKILL.md"], spec_vbs=[],
                  reqs=[("R1", [])])   # no verified_by list
    g, warnings = build_at(d)
    f = fps(warnings)
    check("untested-requirement:spec-four/R1" in f,
          "an EARS requirement with no verified_by edge at all is untested (the EARS teeth)")
    check(not any(x.startswith("dangling-spec") for x in f),
          "an empty verified_by draws no edge -> no dangling-spec (nothing to dangle), only untested")


# ============================================================ 5. shipped + REAL verified_by -> NOT untested
print("[5] a SHIPPED requirement WITH a verified_by to a real eval-case is NOT untested")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    make_eval(d, "ev-five")
    binding_skill(d, "gov5", "spec-five", "shipped",
                  targets=["skills/gov5/SKILL.md"], spec_vbs=[],
                  reqs=[("R1", ["evals/corpus/ev-five"])])
    g, warnings = build_at(d)
    f = fps(warnings)
    check("untested-requirement:spec-five/R1" not in f,
          "a requirement verified by a REAL eval node is tested -> no untested-requirement")
    check(not any(x.startswith("dangling-spec") for x in f),
          "all pointers resolve -> no dangling-spec either")


# ============================================================ 6. ANTI-BACKDOOR: status only ratchets UP
print("[6] anti-backdoor: status:proposed DEFERS untested-requirement but dangling-spec STILL fires")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    # proposed spec, an untested requirement, AND a dangling targets pointer
    binding_skill(d, "gov6", "spec-six", "proposed",
                  targets=["skills/gov6/SKILL.md", "skills/ghost6/SKILL.md"], spec_vbs=[],
                  reqs=[("R1", [])])
    g, warnings = build_at(d)
    f = fps(warnings)
    check("untested-requirement:spec-six/R1" not in f,
          "status:proposed DEFERS untested-requirement (not done yet, not a skipped check)")
    check("dangling-spec:spec-six:skills/ghost6/SKILL.md" in f,
          "status:proposed CANNOT suppress dangling-spec - it always fires (anti-backdoor)")

print("[6b] status:building also defers untested-requirement (only shipped blocks it)")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    binding_skill(d, "gov6b", "spec-six-b", "building",
                  targets=["skills/gov6b/SKILL.md"], spec_vbs=[], reqs=[("R1", [])])
    g, warnings = build_at(d)
    check("untested-requirement:spec-six-b/R1" not in fps(warnings),
          "status:building defers untested-requirement (shipped is the threshold)")


# ============================================================ 7. dormancy / count-neutrality
print("[7] a fully-resolving SHIPPED fixture and a NO-binding fixture each yield ZERO spec warnings")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    make_eval(d, "ev-clean")
    binding_skill(d, "gov7", "spec-seven", "shipped",
                  targets=["skills/gov7/SKILL.md"],
                  spec_vbs=["evals/corpus/ev-clean"],
                  reqs=[("R1", ["evals/corpus/ev-clean"])])
    g, warnings = build_at(d)
    spec_fp = [x for x in fps(warnings) if x.startswith(("dangling-spec", "untested-requirement"))]
    check(spec_fp == [], f"a clean shipped binding produces ZERO spec warnings (got {spec_fp})")

with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    write(os.path.join(d, "skills", "plain", "SKILL.md"),
          "---\nname: plain\ndescription: no binding\n---\nbody.\n")
    g, warnings = build_at(d)
    spec_fp = [x for x in fps(warnings) if x.startswith(("dangling-spec", "untested-requirement"))]
    check(spec_fp == [], "a no-binding artifact produces ZERO spec warnings (dormancy)")


# ============================================================ 8. gate() classification of a spec warning
print("[8] a dangling-spec fingerprint blocks under an empty baseline, is allowed once grandfathered")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    binding_skill(d, "gov8", "spec-eight", "building",
                  targets=["skills/ghost8/SKILL.md"], spec_vbs=[], reqs=[])
    g, warnings = build_at(d)
    fp = "dangling-spec:spec-eight:skills/ghost8/SKILL.md"
    new, grand, stale = ex.gate(warnings, set())           # empty baseline -> strict
    check(fp in {w["fingerprint"] for w in new}, "an un-baselined dangling-spec is NEW (blocks)")
    new2, grand2, stale2 = ex.gate(warnings, {fp})         # grandfathered
    check(fp not in {w["fingerprint"] for w in new2},
          "a grandfathered dangling-spec fingerprint no longer blocks")
    check(fp in {w["fingerprint"] for w in grand2}, "...and is reported as grandfathered")


# ============================================================ 9. --check e2e on a fixture root
print("[9] --check exits non-zero on a dangling pointer; clean once every pointer resolves")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    binding_skill(d, "gov9", "spec-nine", "shipped",
                  targets=["skills/ghost9/SKILL.md"], spec_vbs=[], reqs=[])
    rc, out, err = run("--root", d, "--check")
    blob = out + err
    check(rc != 0, f"--check FAILS (exit {rc}) when a spec pointer dangles")
    check("dangling-spec:spec-nine:skills/ghost9/SKILL.md" in blob,
          "--check names the dangling-spec fingerprint in its block report")
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    binding_skill(d, "gov9b", "spec-nine-b", "shipped",
                  targets=["skills/gov9b/SKILL.md"], spec_vbs=[], reqs=[])
    rc, out, err = run("--root", d, "--check")
    check(rc == 0, f"--check is CLEAN (exit {rc}) when every pointer resolves")


# ============================================================================ done
print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
