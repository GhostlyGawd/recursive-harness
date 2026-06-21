#!/usr/bin/env python3
"""Red-first tests for Spec-Driven Development Phase A (the third cartograph edge class).

Authoritative spec: proposals/2026-06-21-spec-driven-dev.md. Every check below is derived
from an INTENT clause in that proposal, NOT from the extract.py code it drives:

  * Decision B  - the THREE new edge types (specifies/requires/verified_by) live in NEITHER
    REF_EDGE_TYPES NOR DEP_EDGE_TYPES. This is the born_in pattern; it is what makes the
    addition arithmetic-neutral. Guarded here as a tested invariant (the DEP basis test is a
    `<=` subset assertion, so a future leak into DEP would pass silently - we assert the
    NEGATIVE explicitly).
  * Decision A/B - a binding frontmatter block on an artifact yields a spec:<slug> node,
    `specifies` edges to each target, a requirement:<slug>/<rid> node + `requires` edge per
    requirement, and `verified_by` edges at BOTH altitudes (spec->eval-case AND
    requirement->eval-case), the two disambiguated by endpoint node type (one name).
  * Phase A dormancy - an artifact with NO binding yields zero spec/requirement nodes and
    zero new edges; and the new code perturbs none of orphans()/blast_radius()/
    dependencies()/dead_weight on the existing fixtures.
  * Decision C/D - `--query governed-by FILE` reverse-walks `specifies` to the governing
    spec(s) (the create-vs-update check), and returns [] for an ungoverned file.
  * Decision C - `--query traces SPEC` forward-walks requires -> verified_by to render the
    intent -> requirement -> verification tree.
  * Decision B render wiring - each new edge type has an EDGE_COLORS entry (no gray
    fallback) and appears in the text-dump iteration list.

Same runner style as test_query.py / test_audit.py: pure-logic units run in-process on
synthetic graphs built straight from a fixture binding; e2e cases drive the CLI on throwaway
--root fixtures so the trunk stays count-neutral.

Run:  python cartograph/test_spec.py      # exits non-zero on any failure
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = os.path.join(HERE, "extract.py")
ROOT = os.path.dirname(HERE)

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


def S(seq):
    return sorted(seq)


# A FULL binding (Decision A): a skill carrying spec frontmatter that governs two targets,
# is verified at the spec altitude by one eval case, and declares two EARS requirements each
# with its own requirement-altitude verification. The verified_by pointers resolve to
# eval-corpus CASE paths (Decision E), which Phase A discovers as evals:<slug> nodes.
BINDING_FM = """---
name: governed-skill
spec: demo-binding
intent: every targets/verified_by pointer resolves against machine truth or --check fails
targets: [skills/governed-skill/SKILL.md, commands/governed-cmd.md]
verified_by: [evals/corpus/demo-eval]
status: building
requirements:
  - id: R1
    ears: "WHEN a build doc declares spec:, THE SYSTEM SHALL resolve every pointer or --check fails"
    verified_by: [evals/corpus/demo-eval]
  - id: R2
    ears: "WHILE status is shipped, THE SYSTEM SHALL block an EARS requirement with no verified_by"
    verified_by: [evals/corpus/demo-eval-two]
---
governed-skill body. Nothing here should be parsed as a binding pointer.
"""

# A no-binding artifact: dormancy control. Plain frontmatter, no spec: field.
NO_BINDING_FM = """---
name: plain-skill
description: an ordinary skill with no spec binding at all
---
plain body, references skills/governed-skill nowhere meaningful.
"""


def fixture_root(d):
    """Lay down a throwaway harness root: one governed skill (carries the binding), the two
    targets it governs, the two eval-corpus cases its pointers resolve to, plus a plain skill
    (the dormancy control)."""
    write(os.path.join(d, "skills", "governed-skill", "SKILL.md"), BINDING_FM)
    write(os.path.join(d, "skills", "plain-skill", "SKILL.md"), NO_BINDING_FM)
    write(os.path.join(d, "commands", "governed-cmd.md"), "# /governed-cmd\nplain command.\n")
    # eval-corpus cases the verified_by pointers resolve to (Decision E: filesystem existence)
    write(os.path.join(d, "evals", "corpus", "demo-eval", "task.md"), "# demo eval\n")
    write(os.path.join(d, "evals", "corpus", "demo-eval-two", "task.md"), "# demo eval two\n")
    # minimal settings so build() does not choke
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "CLAUDE.md"), "# kernel\n")


def build_fixture_graph(d):
    """Build the graph for a throwaway root in-process (no subprocess) so we can assert on
    nodes/edges directly. Mirrors how the CLI builds it."""
    old = ex.ROOT
    try:
        ex.ROOT = os.path.abspath(d)
        g, warnings, notes, wired = ex.build()
    finally:
        ex.ROOT = old
    return g, warnings


# ============================================================ -1. parser unit edges
# Derived from Decision A's flow-list form + the hand-rolled-parser risk the request flagged
# (a prior dogfood bug was an out-of-domain parser). The quote-aware split must keep a quoted
# element containing a comma intact, and a no-spec frontmatter must parse to None (dormancy).
print("[-1] parse_binding / _yaml_list unit edges")
check(ex.parse_binding("name: x\ndescription: y") is None,
      "frontmatter with NO spec: field parses to None (parser-level dormancy)")
check(ex._yaml_list("[a.md, b.md]") == ["a.md", "b.md"], "plain flow-list splits on commas")
check(ex._yaml_list("['a, b', c.md]") == ["a, b", "c.md"],
      "a QUOTED element containing a comma stays intact (quote-aware split)")
check(ex._yaml_list("evals/corpus/one") == ["evals/corpus/one"], "a bare scalar -> single-element list")
_b = ex.parse_binding("spec: s\nrequirements:\n  - id: R1\n    ears: \"a, b, c clause\"\n"
                      "    verified_by: [evals/corpus/e1]\nstatus: shipped")
check(_b and _b["status"] == "shipped",
      "a top-level field AFTER the requirements block is NOT swallowed into the last requirement")
check(_b and _b["requirements"][0]["ears"] == "a, b, c clause",
      "an EARS clause with commas survives (scalar handler, not flow-split)")


# ============================================================ 0. parse helper exists
print("[0] extract exposes the binding parser + the three new edge-type constants")
check(hasattr(ex, "parse_binding"), "extract exposes parse_binding()")
check(hasattr(ex, "SPEC_EDGE_TYPES"), "extract exposes SPEC_EDGE_TYPES (the third edge class)")
check(getattr(ex, "SPEC_EDGE_TYPES", set()) == {"specifies", "requires", "verified_by"},
      "SPEC_EDGE_TYPES is exactly {specifies, requires, verified_by}")


# ============================================================ 1. THE EXCLUSION INVARIANT
# Decision B (load-bearing): the three new edge types are in NEITHER REF nor DEP. Asserted
# as a POSITIVE guard (born_in pattern) because the DEP basis test is `<=` and would let a
# leak pass silently.
print("[1] EXCLUSION INVARIANT - specifies/requires/verified_by in NEITHER REF NOR DEP")
for et in ("specifies", "requires", "verified_by"):
    check(et not in ex.REF_EDGE_TYPES, f"{et!r} is NOT in REF_EDGE_TYPES (no in-degree/audit perturbation)")
    check(et not in ex.DEP_EDGE_TYPES, f"{et!r} is NOT in DEP_EDGE_TYPES (no dependents/blast/orphan perturbation)")
_spec_types = getattr(ex, "SPEC_EDGE_TYPES", set())
check(_spec_types and _spec_types.isdisjoint(ex.REF_EDGE_TYPES),
      "SPEC_EDGE_TYPES is disjoint from REF_EDGE_TYPES")
check(_spec_types and _spec_types.isdisjoint(ex.DEP_EDGE_TYPES),
      "SPEC_EDGE_TYPES is disjoint from DEP_EDGE_TYPES")


# ============================================================ 2. BINDING PARSE -> nodes+edges
print("[2] a full binding yields spec/requirement/eval nodes + specifies/requires/verified_by edges")
with tempfile.TemporaryDirectory() as d:
    fixture_root(d)
    g, _ = build_fixture_graph(d)

    # the spec node
    check("spec:demo-binding" in g.nodes, "spec:demo-binding node exists")
    check(g.nodes.get("spec:demo-binding", {}).get("type") == "spec",
          "spec node has type 'spec'")
    check(g.nodes.get("spec:demo-binding", {}).get("intent"),
          "spec node carries the intent thesis as metadata")

    edges = {(e["source"], e["target"], e["type"]) for e in g.edges}

    # specifies edges -> each governed target (resolved to its artifact node)
    check(("spec:demo-binding", "skill:governed-skill", "specifies") in edges,
          "specifies edge spec -> skill:governed-skill (target #1)")
    check(("spec:demo-binding", "command:governed-cmd", "specifies") in edges,
          "specifies edge spec -> command:governed-cmd (target #2)")

    # requirement nodes + requires edges
    check("requirement:demo-binding/R1" in g.nodes, "requirement:demo-binding/R1 node exists")
    check("requirement:demo-binding/R2" in g.nodes, "requirement:demo-binding/R2 node exists")
    check(g.nodes.get("requirement:demo-binding/R1", {}).get("type") == "requirement",
          "requirement node has type 'requirement'")
    check(g.nodes.get("requirement:demo-binding/R1", {}).get("ears"),
          "requirement node carries its EARS clause as metadata")
    check(("spec:demo-binding", "requirement:demo-binding/R1", "requires") in edges,
          "requires edge spec -> requirement R1")
    check(("spec:demo-binding", "requirement:demo-binding/R2", "requires") in edges,
          "requires edge spec -> requirement R2")

    # per-case eval nodes (Decision E / Phase A) - the verified_by edges land on these
    check("evals:demo-eval" in g.nodes, "per-case node evals:demo-eval discovered")
    check("evals:demo-eval-two" in g.nodes, "per-case node evals:demo-eval-two discovered")
    check(g.nodes.get("evals:demo-eval", {}).get("type") == "evals",
          "per-case eval node has type 'evals'")

    # verified_by at BOTH altitudes (one name, disambiguated by endpoint node type)
    check(("spec:demo-binding", "evals:demo-eval", "verified_by") in edges,
          "verified_by edge SPEC -> eval-case (spec altitude)")
    check(("requirement:demo-binding/R1", "evals:demo-eval", "verified_by") in edges,
          "verified_by edge REQUIREMENT R1 -> eval-case (requirement altitude)")
    check(("requirement:demo-binding/R2", "evals:demo-eval-two", "verified_by") in edges,
          "verified_by edge REQUIREMENT R2 -> its own eval-case")

    # the two altitudes are the SAME relation name, distinguished only by endpoint type
    vb_src_types = {g.nodes[s]["type"] for s, t, et in edges if et == "verified_by"}
    check(vb_src_types == {"spec", "requirement"},
          "verified_by sources are both spec AND requirement nodes (one name, two altitudes)")


# ============================================================ 2b. ABSENT pointer (Decision E)
# Decision E: the gate resolves pointers by filesystem existence, exactly like dangling-adr -
# a pointer to an ABSENT target still DRAWS an edge to a missing=True node (Phase A does NOT
# warn; warnings are Phase B). Tested so the edge is drawn even when the eval-case dir is gone.
print("[2b] a verified_by pointer to an ABSENT eval-case still draws an edge to a missing node (no warn)")
ABSENT_FM = """---
name: absent-skill
spec: absent-binding
intent: a pointer to a non-existent eval still draws an edge to a missing node
targets: [skills/absent-skill/SKILL.md]
verified_by: [evals/corpus/does-not-exist]
status: proposed
requirements:
  - id: R1
    ears: "WHEN a pointer is dangling, THE SYSTEM SHALL still draw an edge to a missing node"
    verified_by: [evals/corpus/also-missing]
---
body.
"""
with tempfile.TemporaryDirectory() as d:
    write(os.path.join(d, "skills", "absent-skill", "SKILL.md"), ABSENT_FM)
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "CLAUDE.md"), "# kernel\n")
    g, warnings = build_fixture_graph(d)
    edges = {(e["source"], e["target"], e["type"]) for e in g.edges}
    check(("spec:absent-binding", "evals:does-not-exist", "verified_by") in edges,
          "an absent spec-altitude pointer STILL draws a verified_by edge")
    check(g.nodes.get("evals:does-not-exist", {}).get("missing") is True,
          "the absent eval target becomes a node flagged missing=True (dangling-adr mirror)")
    check(("requirement:absent-binding/R1", "evals:also-missing", "verified_by") in edges,
          "an absent requirement-altitude pointer STILL draws a verified_by edge")
    # Phase A draws the edge but does NOT add a warning (no dangling-spec / untested-requirement)
    fps = {w["fingerprint"] for w in warnings}
    check(not any(fp.startswith(("dangling-spec", "untested-requirement")) for fp in fps),
          "Phase A adds NO dangling-spec / untested-requirement warning (that is Phase B)")


# ============================================================ 3. DORMANCY / COUNT-NEUTRALITY
print("[3] dormancy: a no-binding artifact yields ZERO spec/requirement nodes + ZERO new edges")
with tempfile.TemporaryDirectory() as d:
    # ONLY the plain skill - nothing carries a binding
    write(os.path.join(d, "skills", "plain-skill", "SKILL.md"), NO_BINDING_FM)
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "CLAUDE.md"), "# kernel\n")
    g, _ = build_fixture_graph(d)
    spec_nodes = [n for n in g.nodes if n.startswith(("spec:", "requirement:"))]
    new_edges = [e for e in g.edges if e["type"] in ("specifies", "requires", "verified_by")]
    check(spec_nodes == [], "no binding -> zero spec/requirement nodes")
    check(new_edges == [], "no binding -> zero specifies/requires/verified_by edges")

# the spec edges must NOT perturb the existing query/audit arithmetic. Reuse the SAME
# hand-built closure as test_query.py, add spec edges, and assert every closure is unchanged.
print("[3b] adding spec edges to a graph perturbs NO existing closure (orphans/blast/deps/indeg)")
g = ex.Graph()
for nid, ntype in [
    ("command:cmd", "command"), ("skill:sk1", "skill"), ("skill:sk2", "skill"),
    ("skill:sk3", "skill"), ("agent:ag1", "agent"), ("cli:cli1", "cli"),
    ("adr:0001", "adr"),
]:
    g.node(nid, ntype, nid.split(":", 1)[1])
g.edge("command:cmd", "skill:sk1", "cites")
g.edge("skill:sk1", "skill:sk2", "cites")
g.edge("skill:sk2", "adr:0001", "references")
# baseline closures BEFORE spec edges
deps_before = ex.dependencies(g, "command:cmd")
dependents_before = ex.dependents(g, "skill:sk1")
blast_before = ex.blast_radius(g, "adr:0001")
orphans_before = ex.orphans(g)
indeg_before = dict(ex.compute_indegree(g))
# now graft a full spec binding onto the SAME nodes
g.node("spec:s", "spec", "s")
g.node("requirement:s/R1", "requirement", "R1")
g.node("evals:e", "evals", "e")
g.edge("spec:s", "skill:sk1", "specifies")     # governs sk1
g.edge("spec:s", "requirement:s/R1", "requires")
g.edge("spec:s", "evals:e", "verified_by")
g.edge("requirement:s/R1", "evals:e", "verified_by")
check(ex.dependencies(g, "command:cmd") == deps_before, "dependencies(cmd) unchanged by spec edges")
check(ex.dependents(g, "skill:sk1") == dependents_before,
      "dependents(sk1) unchanged - a `specifies` edge must NOT make spec:s a dependent")
check(ex.blast_radius(g, "adr:0001") == blast_before, "blast_radius(adr) unchanged by spec edges")
check("skill:sk1" not in ex.orphans(g), "sk1 is governed but the spec edge does NOT rescue it as a dep")
# the spec node itself must NOT be an orphan candidate (Decision B: keep spec OUT of
# ORPHAN_CANDIDATE_TYPES, like config) - else every authored spec would false-orphan.
check("spec:s" not in ex.orphans(g), "spec:s is NOT in orphans() (spec excluded from candidate types)")
indeg_after = dict(ex.compute_indegree(g))
check(indeg_after.get("skill:sk1") == indeg_before.get("skill:sk1"),
      "in-degree of governed sk1 unchanged - a `specifies` edge is not a reference")


# ============================================================ 4. --query governed-by FILE
print("[4] --query governed-by FILE returns the spec(s) governing it; [] for an ungoverned file")
with tempfile.TemporaryDirectory() as d:
    fixture_root(d)
    rc, out, err = run("--root", d, "--query", "governed-by",
                       "skills/governed-skill/SKILL.md", "--json")
    check(rc == 0, f"governed-by on a governed file exits 0 (got {rc}; err={err[-200:]})")
    try:
        j = json.loads(out)
        ids = [s["id"] if isinstance(s, dict) else s for s in j["governed_by"]]
        ok = "spec:demo-binding" in ids
    except Exception as e:
        ok = False
        print("    parse err:", e, out[:200])
    check(ok, "governed-by names spec:demo-binding for a governed target")

    # an ungoverned file -> empty result, exit 0 (not an error)
    rc2, out2, err2 = run("--root", d, "--query", "governed-by",
                          "commands/governed-cmd.md", "--json")
    # governed-cmd IS a target of demo-binding, so it should also be governed
    try:
        ids2 = [s["id"] if isinstance(s, dict) else s for s in json.loads(out2)["governed_by"]]
        ok2 = "spec:demo-binding" in ids2
    except Exception:
        ok2 = False
    check(rc2 == 0 and ok2, "governed-by resolves the SECOND target (command) to the same spec")

    # a genuinely ungoverned file
    rc3, out3, err3 = run("--root", d, "--query", "governed-by",
                          "skills/plain-skill/SKILL.md", "--json")
    try:
        ids3 = [s["id"] if isinstance(s, dict) else s for s in json.loads(out3)["governed_by"]]
        ok3 = ids3 == []
    except Exception:
        ok3 = False
    check(rc3 == 0 and ok3, "governed-by on an UNGOVERNED file returns [] and exits 0 (not an error)")


# ============================================================ 5. --query traces SPEC
print("[5] --query traces SPEC forward-walks requires -> verified_by into the trace tree")
with tempfile.TemporaryDirectory() as d:
    fixture_root(d)
    rc, out, err = run("--root", d, "--query", "traces", "spec:demo-binding", "--json")
    check(rc == 0, f"traces on a real spec exits 0 (got {rc}; err={err[-200:]})")
    try:
        j = json.loads(out)
        req_ids = {r["id"] for r in j["requirements"]}
        # each requirement carries its verifications
        r1 = next(r for r in j["requirements"] if r["id"] == "requirement:demo-binding/R1")
        ok = ("requirement:demo-binding/R1" in req_ids
              and "requirement:demo-binding/R2" in req_ids
              and "evals:demo-eval" in (r1.get("verified_by") or []))
    except Exception as e:
        ok = False
        print("    parse err:", e, out[:300])
    check(ok, "traces names both requirements and each requirement's verified_by eval-case")

    # spec-altitude verifications surface too
    try:
        ok_spec = "evals:demo-eval" in (json.loads(out).get("verified_by") or [])
    except Exception:
        ok_spec = False
    check(ok_spec, "traces surfaces the spec-altitude verified_by eval-case")


# ============================================================ 6. RENDER WIRING
print("[6] each new edge type has an EDGE_COLORS entry (no gray fallback) + is in the render list")
GRAY = "#556"
for et in ("specifies", "requires", "verified_by"):
    color = ex.EDGE_COLORS.get(et)
    check(color is not None and color != GRAY,
          f"{et!r} has a distinct EDGE_COLORS entry (got {color!r}, not the gray fallback)")
# distinct colors per type (not all the same)
colors = {ex.EDGE_COLORS.get(et) for et in ("specifies", "requires", "verified_by")}
check(len(colors) == 3, "the three new edge types have three DISTINCT colors")

# the text dump must iterate the new types (else they never render). Drive a fixture that
# actually has the edges and assert they appear in the text dump's EDGES section.
with tempfile.TemporaryDirectory() as d:
    fixture_root(d)
    rc, out, err = run("--root", d)   # default text dump
    text = out + err
    check("specifies" in text, "text dump renders the `specifies` edge group")
    check("requires" in text, "text dump renders the `requires` edge group")
    check("verified_by" in text, "text dump renders the `verified_by` edge group")


# ============================================================ 7. ROLE wiring
print("[7] spec/requirement node types have a ROLE_BY_TYPE entry (not the '?' fallback)")
check(ex.ROLE_BY_TYPE.get("spec", "?") != "?", "spec type has a curated role")
check(ex.ROLE_BY_TYPE.get("requirement", "?") != "?", "requirement type has a curated role")


# ============================================================ 8. --query DISCOVERABILITY
# Decision C/D wiring guard: the two new verbs must be advertised in the user-facing help,
# not just implemented. The --query argparse help string (and the run_query unknown-kind
# error) is the only place a reader learns governed-by/traces exist. If that list regresses
# back to the old blast-radius|...|node set, this goes red. We collapse whitespace before
# asserting because argparse wraps long help lines (splitting `governed-by` across a line);
# the literal hyphen survives the collapse, the inserted newline/indent does not.
print("[8] --query help advertises BOTH new verbs (governed-by + traces)")
_, help_out, _ = run("--help")
help_flat = re.sub(r"\s+", "", help_out)
check("governed-by" in help_flat, "--help --query line advertises the `governed-by` verb")
check("traces" in help_flat, "--help --query line advertises the `traces` verb")
# the run_query unknown-kind error surfaces the same verb list on a single line
_, _, unk_err = run("--query", "no-such-verb")
check("governed-by" in unk_err and "traces" in unk_err,
      "unknown --query kind error lists both new verbs")


# ============================================================================ done
print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
