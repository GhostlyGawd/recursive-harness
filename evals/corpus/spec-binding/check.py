#!/usr/bin/env python3
"""Objective grader for spec-binding — the guard for the SDD spec-binding gate (Phase B).

argv[1] = sandbox dir (unused). This case validates the LIVE spec-pointer gate
(cartograph/extract.py --check: the `dangling-spec` + `untested-requirement` classes,
proposal 2026-06-21-spec-driven-dev.md Decision E) against throwaway --root fixtures, so
it resolves the repo root from its own location (evals/corpus/spec-binding/check.py -> 4
dirs up) rather than the sandbox, exactly like cartograph-gate's check.py.

It is the guard for the SPEC half of the gate: cartograph-gate already pins the generic
mechanics (orphan-hook/dangling-adr, baseline grandfathering, --check/--write-baseline
mutual exclusion); this pins what a refactor could silently neuter in the spec layer -
the two spec warn classes and the anti-backdoor invariant (status: can only ratchet
strictness UP; it can never suppress dangling-spec).
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
extract = os.path.join(ROOT, "cartograph", "extract.py")


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def run(*args):
    return subprocess.run([sys.executable, extract, *args],
                          capture_output=True, text=True)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def minimal_root(d):
    # the two files build() always needs; no hooks dir -> no orphan-hook noise, so the only
    # warnings a fixture can raise are the spec classes under test.
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "CLAUDE.md"), "# kernel\n")


def binding(d, slug, status, targets="", verified_by="", requirements=""):
    fm = (f"---\nname: g\nspec: {slug}\nintent: spec-binding guard fixture\n"
          f"{targets}{verified_by}status: {status}\n{requirements}---\nbody.\n")
    write(os.path.join(d, "skills", "g", "SKILL.md"), fm)


if not os.path.exists(extract):
    fail("cartograph/extract.py missing")

# 0. the SPEC gate is dormant/green on the clean trunk (no live bindings -> zero spec
#    warnings; the committed baseline grandfathers nothing).
r = run("--check")
if r.returncode != 0:
    fail("--check on the clean trunk did not exit 0: " + (r.stdout + r.stderr)[-300:])

# 1-2. a binding whose verified_by: pointer resolves to nothing must BLOCK + name
#      dangling-spec; grandfathering it (--write-baseline) must un-block it.
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    binding(d, "case-spec", "building",
            targets="targets: [skills/g/SKILL.md]\n",
            verified_by="verified_by: [evals/corpus/does-not-exist]\n")
    bl = os.path.join(d, "bl.json")
    r = run("--root", d, "--check", bl)
    if r.returncode != 1:
        fail(f"dangling-spec fixture did not block (--check exit {r.returncode}, want 1)")
    if "dangling-spec:case-spec:evals/corpus/does-not-exist" not in (r.stdout + r.stderr):
        fail("gate blocked but did not name the dangling-spec fingerprint")
    if run("--root", d, "--write-baseline", bl).returncode != 0:
        fail("--write-baseline failed on the dangling-spec fixture")
    r = run("--root", d, "--check", bl)
    if r.returncode != 0:
        fail(f"grandfathered dangling-spec still blocks (--check exit {r.returncode}, want 0)")

# 3. a status: shipped spec with an EARS requirement carrying no verified_by must BLOCK +
#    name untested-requirement (the EARS teeth, fired only at the shipped threshold).
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    binding(d, "ship-spec", "shipped",
            targets="targets: [skills/g/SKILL.md]\n",
            requirements="requirements:\n  - id: R1\n    ears: \"WHEN x THE SYSTEM SHALL y\"\n")
    r = run("--root", d, "--check", os.path.join(d, "bl.json"))
    if r.returncode != 1:
        fail(f"untested-requirement fixture did not block (--check exit {r.returncode}, want 1)")
    if "untested-requirement:ship-spec/R1" not in (r.stdout + r.stderr):
        fail("gate blocked but did not name the untested-requirement fingerprint")

# 3b. the shipped-only THRESHOLD (the other half of the ratchet): the SAME untested
#     requirement at status: building must NOT fire untested-requirement - proposed/building
#     defer it ("not done yet"). Pins the threshold against an OVER-strict regression that
#     would block in-progress work by firing the class at every status.
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    binding(d, "build-spec", "building",
            targets="targets: [skills/g/SKILL.md]\n",
            requirements="requirements:\n  - id: R1\n    ears: \"WHEN x THE SYSTEM SHALL y\"\n")
    r = run("--root", d, "--check", os.path.join(d, "bl.json"))
    if r.returncode != 0:
        fail(f"status: building blocked an untested requirement (--check exit {r.returncode}, "
             "want 0 - shipped is the threshold): " + (r.stdout + r.stderr)[-300:])
    if "untested-requirement" in (r.stdout + r.stderr):
        fail("status: building named untested-requirement (over-strict; shipped-only threshold broken)")

# 4. ANTI-BACKDOOR: status: proposed CANNOT suppress dangling-spec - a dangling pointer
#    blocks at ANY status (machine truth, never trusts status:).
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    binding(d, "prop-spec", "proposed", targets="targets: [skills/ghost/SKILL.md]\n")
    r = run("--root", d, "--check", os.path.join(d, "bl.json"))
    if r.returncode != 1:
        fail("status: proposed suppressed dangling-spec (anti-backdoor breach)")
    if "dangling-spec:prop-spec:skills/ghost/SKILL.md" not in (r.stdout + r.stderr):
        fail("a proposed-status dangling pointer did not fire dangling-spec")

# 5. a fully-resolving SHIPPED binding must NOT false-positive (every targets/verified_by
#    pointer resolves, every requirement is verified) -> --check clean.
with tempfile.TemporaryDirectory() as d:
    minimal_root(d)
    write(os.path.join(d, "evals", "corpus", "ev", "task.md"), "# ev\n")
    binding(d, "clean-spec", "shipped",
            targets="targets: [skills/g/SKILL.md]\n",
            verified_by="verified_by: [evals/corpus/ev]\n",
            requirements=("requirements:\n  - id: R1\n    ears: \"WHEN x THE SYSTEM SHALL y\"\n"
                          "    verified_by: [evals/corpus/ev]\n"))
    r = run("--root", d, "--check", os.path.join(d, "bl.json"))
    if r.returncode != 0:
        fail("a fully-resolving shipped binding false-positived (--check exit "
             f"{r.returncode}): " + (r.stdout + r.stderr)[-300:])

print("ok (trunk green; dangling-spec blocks+names+grandfathers; untested-requirement "
      "blocks at shipped; status can't suppress dangling-spec; clean binding no false-positive)")
sys.exit(0)
