#!/usr/bin/env python3
"""Guard for cartograph/atlas.py - the Atlas generator.

The cartograph's own stated risk is a "silent edge drop"; one level up, the Atlas's
risk is a **silent SECTION (or diagram) drop** - a refactor that quietly removes a
lens from the committed map, leaving a map that looks complete but isn't. This test
pins the generator's contract: every structural lens present, the diagrams present,
the pulse present, curated overlays flagged, and build_atlas() read-only.

Staleness (committed ATLAS.md vs the live graph) is reported as an ADVISORY NOTE,
never a failure: a hard "regenerate-or-CI-fails" gate would tax every structural PR,
and the build stamp + `/atlas` already make staleness visible. Sync is a ritual, not
a blocker.

Pure stdlib (CI runs `python3 cartograph/test_atlas.py`, no pip). Wired into
.github/workflows/ci.yml; tests/test_ci_coverage.py enforces that wiring.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import atlas  # noqa: E402  (also makes `extract` importable - atlas imports it)
import extract  # noqa: E402

FAIL = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  ({detail})"))
    if not cond:
        FAIL.append(name)


structural, pulse = atlas.build_atlas()

# (1) every structural lens present - the silent-section-drop guard. Anchored on the
# stable heading prefixes (the descriptive tail may evolve; the lens must not vanish).
SECTIONS = [
    "## 1. System-of-systems",
    "## 2. The three self-improvement loops",
    "## 3. Lifecycle",
    "## 4. State dataflow",
    "## 5. Dependency hotspots",
    "## 6. Taxonomy",
    "## 7. Subsystem inventory",
    "## 8. Gaps",
]
for h in SECTIONS:
    check(f"structural lens present: {h!r}", h in structural, "section vanished from ATLAS.md")

# (2) multiple visualization styles - at least one diagram per major structural view.
nblocks = structural.count("```mermaid")
check("at least 4 mermaid diagrams in the structural map", nblocks >= 4,
      f"only {nblocks} mermaid blocks - a diagram lens was dropped")

# (3) the pulse (live-strain companion) and its three answers: friction / load / bugs.
check("pulse: strain header present", "Where the harness strains" in pulse)
check("pulse: friction-by-category lens", "prediction reliability by category" in pulse)
check("pulse: load (fired skills) lens", "most-fired skills" in pulse)
check("pulse: bug-cluster lens", "Where bugs cluster" in pulse)

# (4) honesty contract - curated overlays must be FLAGGED, never passed as extracted
# truth (the same invariant extract.py keeps for role/loop).
check("curated overlays flagged in the structural map", "[curated overlay]" in structural)
check("extracted views labelled as extracted", "[extracted" in structural)

# (5) read-only: building the docs must mutate nothing under cartograph/. (main() writes
# the files; build_atlas() only assembles strings.) Snapshot mtimes across a 2nd build.
def _snapshot():
    return {f: os.path.getmtime(os.path.join(HERE, f))
            for f in os.listdir(HERE) if os.path.isfile(os.path.join(HERE, f))}


before = _snapshot()
atlas.build_atlas()
check("build_atlas() is read-only (writes nothing under cartograph/)", before == _snapshot(),
      "a file under cartograph/ changed during build_atlas()")

# (6) ADVISORY staleness note (never a failure): committed ATLAS.md node count vs live.
committed = os.path.join(HERE, "ATLAS.md")
if os.path.exists(committed):
    m = re.search(r"Nodes \| \*\*(\d+)\*\*", open(committed, encoding="utf-8").read())
    if m:
        g, _w, _n, _wd = extract.build()
        live = len(g.nodes)
        if int(m.group(1)) != live:
            print(f"NOTE  committed ATLAS.md shows {m.group(1)} nodes; live graph has "
                  f"{live} - run /atlas to re-sync (advisory, not a failure)")

if FAIL:
    print(f"\nFAILED: {len(FAIL)} check(s)")
    sys.exit(1)
print(f"\ntest_atlas: all checks passed ({len(SECTIONS)} lenses, {nblocks} diagrams)")
sys.exit(0)
