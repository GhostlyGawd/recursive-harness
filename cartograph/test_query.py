#!/usr/bin/env python3
"""Red-first tests for cartograph A - the Structural Oracle (`extract.py --context` /
`--query`).

The oracle turns the already-extracted graph into a thing the AGENT consults before
editing: "what does this file use, what uses it, what's the blast radius if I change it".
Its load-bearing contract is DIRECTION - edges are consumer->provider (`source` depends on
`target`), so dependents (who breaks) are PREDECESSORS and dependencies (what it uses) are
SUCCESSORS, and provenance (`born_in`) is lineage that must NEVER count as a dependency. The
hand-built fixture below has a known closure (incl. a cycle and a lineage edge) so every
direction + transitivity claim is asserted exactly, not just smoke-tested.

Self-contained, same runner style as test_audit.py. Pure-logic units run in-process on the
synthetic graph; e2e cases drive the CLI on the real trunk and assert read-only + clean errors.

Run:  python cartograph/test_query.py      # exits non-zero on any failure
"""
import importlib.util
import json
import os
import subprocess
import sys

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


def make_fixture():
    """A tiny graph with a HAND-VERIFIED closure. Edges are consumer->provider:
        command:cmd --cites-->    skill:sk1            (cmd uses sk1)
        command:cmd --spawns-->   agent:ag1
        skill:sk1   --invokes-->  cli:cli1
        skill:sk1   --cites-->    skill:sk2
        skill:sk2   --references->adr:0001
        hook:hk1    --fires_on--> event:ev1            (hk1 is a DEP-source)
        hook:hk1    --touches-->  state:st1
        skill:sk1   --born_in-->  session:ses1         (LINEAGE - excluded from DEP)
        skill:scc_a --cites-->    skill:scc_b          (a cycle, both ways)
        skill:scc_b --cites-->    skill:scc_a
        skill:sk3                                       (provider, zero dependents = orphan)
    """
    g = ex.Graph()
    for nid, ntype in [
        ("command:cmd", "command"), ("skill:sk1", "skill"), ("skill:sk2", "skill"),
        ("skill:sk3", "skill"), ("agent:ag1", "agent"), ("cli:cli1", "cli"),
        ("adr:0001", "adr"), ("hook:hk1", "hook"), ("event:ev1", "event"),
        ("state:st1", "state"), ("session:ses1", "session"),
        ("skill:scc_a", "skill"), ("skill:scc_b", "skill"),
    ]:
        g.node(nid, ntype, nid.split(":", 1)[1])
    g.edge("command:cmd", "skill:sk1", "cites")
    g.edge("command:cmd", "agent:ag1", "spawns")
    g.edge("skill:sk1", "cli:cli1", "invokes")
    g.edge("skill:sk1", "skill:sk2", "cites")
    g.edge("skill:sk2", "adr:0001", "references")
    g.edge("hook:hk1", "event:ev1", "fires_on")
    g.edge("hook:hk1", "state:st1", "touches")
    g.edge("skill:sk1", "session:ses1", "born_in")     # lineage
    g.edge("skill:scc_a", "skill:scc_b", "cites")
    g.edge("skill:scc_b", "skill:scc_a", "cites")       # cycle
    return g


G = make_fixture()


def S(seq):
    return sorted(seq)


# ===================================================== 0. DEP_EDGE_TYPES basis
print("[0] DEP_EDGE_TYPES = REF_EDGE_TYPES + touches, and EXCLUDES born_in lineage")
check(hasattr(ex, "DEP_EDGE_TYPES"), "extract exposes DEP_EDGE_TYPES")
check("born_in" not in getattr(ex, "DEP_EDGE_TYPES", set()),
      "born_in (lineage) is NOT a dependency edge")
check({"cites", "invokes", "spawns", "references", "fires_on", "touches"}
      <= getattr(ex, "DEP_EDGE_TYPES", set()),
      "the seven+ real reference/wiring edges ARE dependency edges (incl. touches)")


# ===================================================== 1. dependencies() = direct successors
print("[1] dependencies(node) = what it USES (direct successors over DEP edges)")
check(S(ex.dependencies(G, "command:cmd")) == ["agent:ag1", "skill:sk1"],
      "cmd uses sk1 (cites) + ag1 (spawns)")
check(S(ex.dependencies(G, "skill:sk1")) == ["cli:cli1", "skill:sk2"],
      "sk1 uses cli1 (invokes) + sk2 (cites) - NOT session:ses1 (born_in is lineage)")
check(ex.dependencies(G, "skill:sk3") == [], "an orphan provider uses nothing")


# ===================================================== 2. dependents() = direct predecessors
print("[2] dependents(node) = what USES it (direct predecessors over DEP edges)")
check(S(ex.dependents(G, "skill:sk1")) == ["command:cmd"], "sk1 is used by cmd")
check(S(ex.dependents(G, "skill:sk2")) == ["skill:sk1"], "sk2 is used by sk1")
check(S(ex.dependents(G, "cli:cli1")) == ["skill:sk1"], "cli1 is invoked by sk1")
check(S(ex.dependents(G, "event:ev1")) == ["hook:hk1"], "ev1 is fired-on by hk1")
check(S(ex.dependents(G, "state:st1")) == ["hook:hk1"], "st1 is touched by hk1 (touches IS a dep)")
check(ex.dependents(G, "session:ses1") == [],
      "a session has NO dependents - born_in must never be reversed into a dependency")


# ===================================================== 3. blast_radius() = transitive dependents
print("[3] blast_radius(node) = transitive dependents + shortest distance, cycle-safe")
br = ex.blast_radius(G, "adr:0001")
check(br == {"skill:sk2": 1, "skill:sk1": 2, "command:cmd": 3},
      "changing adr:0001 ripples sk2(1) -> sk1(2) -> cmd(3)")
check(ex.blast_radius(G, "cli:cli1") == {"skill:sk1": 1, "command:cmd": 2},
      "cli1's blast = sk1(1) -> cmd(2)")
check(ex.blast_radius(G, "skill:sk1") == {"command:cmd": 1}, "sk1's blast = just cmd(1)")
check(ex.blast_radius(G, "session:ses1") == {},
      "a session has empty blast radius (lineage never propagates)")
check(ex.blast_radius(G, "skill:scc_a") == {"skill:scc_b": 1},
      "a cycle TERMINATES: scc_a's blast = {scc_b}, the start node is not re-included")


# ===================================================== 4. find_path() over DEP edges, directional
print("[4] find_path(a,b) = a real dependency path a->b, or None - and it is DIRECTIONAL")
check(ex.find_path(G, "command:cmd", "adr:0001")
      == ["command:cmd", "skill:sk1", "skill:sk2", "adr:0001"],
      "cmd depends-transitively on adr:0001 via sk1 -> sk2")
check(ex.find_path(G, "skill:sk2", "skill:sk1") is None,
      "no reverse path: sk1 depends on sk2, not vice-versa (direction matters)")
check(ex.find_path(G, "command:cmd", "skill:sk3") is None, "no path to an orphan")
check(ex.find_path(G, "skill:sk1", "skill:sk1") == ["skill:sk1"], "path(x,x) is the trivial [x]")


# ===================================================== 5. orphans() = unused provider defs
print("[5] orphans() = provider-type nodes with zero dependents (NOT every hook)")
check(ex.orphans(G) == ["skill:sk3"],
      "only the defined-but-unused skill is an orphan; the wired hook is not, lineage/entry excluded")


# ===================================================== 6. resolve_node(): id / name / file / miss
print("[6] resolve_node(target) accepts id, bare name, file path; reports miss vs ambiguous")
check(ex.resolve_node(G, "skill:sk1") == ("skill:sk1", ["skill:sk1"]), "exact id resolves to itself")
check(ex.resolve_node(G, "sk1")[0] == "skill:sk1", "unique bare name resolves")
nid, cands = ex.resolve_node(G, "nope_missing")
check(nid is None and cands == [], "a miss returns (None, []) - never a crash")
# ambiguity: add a second 'dup' under two types
g2 = make_fixture()
g2.node("skill:dup", "skill", "dup")
g2.node("agent:dup", "agent", "dup")
nid2, cands2 = ex.resolve_node(g2, "dup")
check(nid2 is None and S(cands2) == ["agent:dup", "skill:dup"],
      "an ambiguous bare name returns (None, [candidates]) so the CLI can list them")


# ===================================================== 7. e2e: --context on a real file
print("[7] e2e: --context FILE on the real trunk prints a directional brief, exit 0")
rc, out, err = run("--context", "commands/retro.md")
text = out + err
check(rc == 0, f"--context commands/retro.md exits 0 (got {rc})")
check("command:retro" in text, "brief names the resolved node id")
check("dependencies" in text.lower() and "dependents" in text.lower(),
      "brief shows BOTH directions (what it uses AND what uses it)")
check("blast" in text.lower(), "brief shows a blast-radius line")

rc, out, err = run("--context", "commands/retro.md", "--json")
check(rc == 0, "--context --json exits 0")
try:
    j = json.loads(out)
    ok = (j["node"]["id"] == "command:retro"
          and "dependencies" in j and "dependents" in j
          and "blast_radius" in j and "flags" in j)
except Exception:
    ok = False
check(ok, "--context --json has {node,dependencies,dependents,blast_radius,flags}")

# The ACTOR case - the plan's whole justification (L44-52): a HOOK has a near-empty
# blast-radius but rich DOWNSTREAM deps (fires_on event / touches state). A provider-only
# stub passes the command case above but FAILS here. Verified anchors against the real graph:
# hook:log_correction fires_on event:UserPromptSubmit + touches state:corrections.
rc, out, err = run("--context", "hooks/log_correction.py", "--json")
try:
    j = json.loads(out)
    deps_via = {d.get("via") for d in j["dependencies"]}
    ok = (j["node"]["id"] == "hook:log_correction" and j["node"]["type"] == "hook"
          and ("fires_on" in deps_via or "touches" in deps_via)   # actor downstream IS shown
          and "blast_radius" in j and "dependents" in j)
except Exception:
    ok = False
check(ok, "--context on a HOOK surfaces its downstream deps (fires_on/touches), not just dependents")

rc, out, err = run("--context", "hooks/log_correction.py")
text = out + err
check(rc == 0 and "dependencies" in text.lower() and "dependents" in text.lower(),
      "hook brief renders BOTH directions in text - the actor case the oracle exists for")


# ===================================================== 8. e2e: --query kinds on real nodes
print("[8] e2e: --query blast-radius / dependencies / path / orphans on the real trunk")
rc, out, err = run("--query", "blast-radius", "skill:retrospection", "--json")
check(rc == 0, "--query blast-radius <node> --json exits 0")
try:
    j = json.loads(out)
    ok = j["kind"] == "blast-radius" and isinstance(j["result"], list)
except Exception:
    ok = False
check(ok, "blast-radius json = {target,kind,result:[...]}")

rc, out, err = run("--query", "dependencies", "command:retro", "--json")
try:
    j = json.loads(out)
    ok = j["kind"] == "dependencies" and isinstance(j["result"], list)
except Exception:
    ok = False
check(rc == 0 and ok, "dependencies json = {target,kind,result:[...]} (A8 shape)")

rc, out, err = run("--query", "orphans", "--json")
check(rc == 0, "--query orphans --json exits 0")
try:
    ok = isinstance(json.loads(out)["orphans"], list)
except Exception:
    ok = False
check(ok, "orphans json = {orphans:[...]}")

# path between two real nodes KNOWN connected: command:retro --invokes--> cli:stats (verified
# against the live graph). Assert a NON-NULL path with correct endpoints, NOT just exit 0 - a
# 'no path' stub would satisfy exit 0 and leave path-finding unexercised (the [BLOCKER] fix).
rc, out, err = run("--query", "path", "command:retro", "cli:stats", "--json")
try:
    j = json.loads(out)
    ok = (rc == 0 and j["path"] and j["path"][0] == "command:retro"
          and j["path"][-1] == "cli:stats" and j["length"] == len(j["path"]) - 1)
except Exception:
    ok = False
check(ok, "path command:retro->cli:stats is a real non-null path {a,b,path,length}")


# ===================================================== 9. e2e: clean errors, never a traceback
print("[9] e2e: unresolvable target -> non-zero, one-line message, NO traceback")
rc, out, err = run("--context", "does/not/exist.xyz")
text = out + err
check(rc != 0, "unmapped file exits non-zero")
check("Traceback" not in text, "no python traceback leaks to the user")

rc, out, err = run("--query", "blast-radius", "zzz_nonexistent_node")
check(rc != 0 and "Traceback" not in (out + err), "unresolvable --query target -> clean non-zero")


# ===================================================== 10. e2e: the oracle is READ-ONLY
print("[10] e2e: running the oracle mutates nothing (git stays clean, index.html unchanged)")
html = os.path.join(HERE, "index.html")
before_html = os.path.getmtime(html) if os.path.exists(html) else None
porc_before = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                             capture_output=True, text=True).stdout
run("--context", "commands/retro.md")
run("--query", "blast-radius", "skill:retrospection")
run("--query", "orphans")
porc_after = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                            capture_output=True, text=True).stdout
after_html = os.path.getmtime(html) if os.path.exists(html) else None
check(porc_before == porc_after, "git porcelain unchanged after oracle runs (no new/edited files)")
check(before_html == after_html, "index.html not rewritten by an oracle command")


# ============================================================================ done
print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
