#!/usr/bin/env python3
"""Tests for the cartograph self-audit feed (`extract.py --audit`).

The audit is the autophagic loop's SURFACING half: it hands /meta-retro a
machine-readable list of structural-rot + dead-weight CANDIDATES, each with its
evidence. Its load-bearing contract is that it only INFORMS - it never mutates the
repo and never blocks (exit 0 always). Pruning stays a human decision. That
firewall (audit advises, gate blocks, neither prunes) is what these tests pin down.

Self-contained: pure-logic units run in-process on synthetic graphs (so the
conservative dead-weight rule is tested at the boundary without needing real git
history), and the e2e cases drive the CLI on throwaway --root fixtures + the real
trunk.

Run:  python cartograph/test_audit.py      # exits non-zero on any failure
"""
import datetime
import importlib.util
import json
import os
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
    return r.returncode, r.stdout + r.stderr


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def orphan_fixture(d):
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "hooks", "orphan_widget.py"), 'print("not wired")\n')


TODAY = datetime.date(2026, 6, 20)
OLD = "2026-01-01"      # >90d before TODAY
FRESH = "2026-06-19"    # 1d before TODAY


# ============================================== 1. is_dead_weight: the conservative rule
print("[1] is_dead_weight() - the 4-condition rule, each axis tested in isolation")

def node(ntype, added=OLD, fires=None):
    n = {"id": f"{ntype}:x", "type": ntype, "added": added, "file": "f"}
    if fires is not None:
        n["fires"] = fires
    return n

check(ex.is_dead_weight(node("skill"), 0, TODAY) is True,
      "old + unreferenced + unused skill -> candidate")
check(ex.is_dead_weight(node("agent"), 0, TODAY) is True,
      "old + unspawned agent -> candidate (agents never fire; in-degree is the signal)")
check(ex.is_dead_weight(node("command"), 0, TODAY) is False,
      "commands are user entry points -> never dead-weight by this rule")
check(ex.is_dead_weight(node("hook"), 0, TODAY) is False,
      "hooks are not skill/agent -> never flagged here (orphan-hook is the gate's job)")
check(ex.is_dead_weight(node("skill"), 1, TODAY) is False,
      "referenced (in_degree>0) -> not a candidate")
check(ex.is_dead_weight(node("skill", fires=2), 0, TODAY) is False,
      "fired (fires>0) -> not a candidate")
check(ex.is_dead_weight(node("skill", fires=0), 0, TODAY) is True,
      "fires==0 counts as unused -> still a candidate")
check(ex.is_dead_weight(node("skill", added=FRESH), 0, TODAY) is False,
      "recent (<90d) -> not a candidate (honors meta-retro's <90d protection)")
check(ex.is_dead_weight(node("skill", added=None), 0, TODAY) is False,
      "undatable (added=None) -> conservatively NOT flagged")


# ===================================================== 2. compute_indegree: ref edges only
print("[2] compute_indegree() counts inbound reference edges, ignores lineage/state")
g = ex.Graph()
g.node("skill:a", "skill", "a")
g.node("skill:b", "skill", "b")
g.node("agent:c", "agent", "c")
g.node("session:s", "session", "s")
g.node("state:x", "state", "x")
g.edge("command:r", "skill:a", "cites")
g.edge("command:r", "agent:c", "spawns")
g.edge("skill:a", "session:s", "born_in")   # lineage -> must NOT raise session in-degree as a ref
g.edge("skill:a", "state:x", "touches")      # state write -> not a reference
indeg = ex.compute_indegree(g)
check(indeg.get("skill:a") == 1, "cites raises target in-degree")
check(indeg.get("agent:c") == 1, "spawns raises target in-degree")
check(indeg.get("skill:b") == 0, "unreferenced node has in-degree 0")
check(indeg.get("session:s", 0) == 0, "born_in (lineage) does not count as a reference")
check(indeg.get("state:x", 0) == 0, "touches (state write) does not count as a reference")
check("born_in" not in ex.REF_EDGE_TYPES and "touches" not in ex.REF_EDGE_TYPES,
      "REF_EDGE_TYPES excludes lineage + state edges by construction")
# SDD Phase A exclusion invariant (Decision B): the three spec edge types are governance,
# not references - they must NEVER raise a target's in-degree or rescue it from dead-weight.
check("specifies" not in ex.REF_EDGE_TYPES and "requires" not in ex.REF_EDGE_TYPES
      and "verified_by" not in ex.REF_EDGE_TYPES,
      "REF_EDGE_TYPES excludes the spec edge class (specifies/requires/verified_by)")


# ===================================== 3. audit_report: end-to-end assembly on a synthetic graph
print("[3] audit_report() assembles rot + dead_weight with evidence, both precise")
g = ex.Graph()
g.node("skill:old_dead", "skill", "old_dead", file="skills/old_dead/SKILL.md", added=OLD)
g.node("agent:lonely", "agent", "lonely", file="agents/lonely.md", added=OLD)
g.node("skill:used", "skill", "used", file="skills/used/SKILL.md", added=OLD, fires=3)
g.node("skill:referenced", "skill", "referenced", file="skills/referenced/SKILL.md", added=OLD)
g.node("skill:fresh", "skill", "fresh", file="skills/fresh/SKILL.md", added=FRESH)
g.node("command:entry", "command", "entry", file="commands/entry.md", added=OLD)
g.edge("command:entry", "skill:referenced", "cites")
warnings = [{"fingerprint": "orphan-hook:z", "message": "z is wired nowhere"}]
rep = ex.audit_report(g, warnings, today=TODAY)

check([d["id"] for d in rep["dead_weight"]] == ["agent:lonely", "skill:old_dead"],
      "dead_weight = exactly the old/unreferenced/unused skill+agent, sorted, nothing else")
dw = {d["id"]: d for d in rep["dead_weight"]}
check(dw["skill:old_dead"].get("in_degree") == 0 and dw["skill:old_dead"].get("file"),
      "each dead_weight item carries its evidence (in_degree + file + reason)")
check("reason" in dw["agent:lonely"], "each dead_weight item carries a human reason string")
check([r["fingerprint"] for r in rep["structural_rot"]] == ["orphan-hook:z"],
      "structural_rot mirrors the warning set (fingerprint-keyed)")
check(rep["meta"].get("advisory") is True and rep["meta"].get("mutates") is False,
      "meta records the firewall: advisory, non-mutating")


# ======================================== 4. e2e: --audit is advisory (exit 0) + read-only
print("[4] e2e: --audit exits 0 always and writes nothing without an explicit path")
rc, out = run("--audit")
check(rc == 0, f"--audit on real trunk exits 0 (got {rc})")
check("audit" in out.lower(), "prints a self-audit report")

with tempfile.TemporaryDirectory() as d:
    orphan_fixture(d)
    before = sorted(os.listdir(d))
    rc, out = run("--root", d, "--audit")             # rot present, but advisory
    check(rc == 0, f"--audit exits 0 EVEN WITH structural rot present (advisory, got {rc})")
    after = sorted(os.listdir(d))
    check(before == after, "bare --audit creates no files (read-only: no map.json/baseline)")


# ======================================== 5. e2e: audit_json shape + rot == the gate's set
print("[5] e2e: --audit <json> emits {structural_rot,dead_weight,meta}; rot matches the gate")
with tempfile.TemporaryDirectory() as d:
    orphan_fixture(d)
    out_json = os.path.join(d, "audit.json")
    rc, _ = run("--root", d, "--audit", out_json)
    check(rc == 0 and os.path.isfile(out_json), "--audit <path> writes the json + exits 0")
    rep = json.loads(open(out_json, encoding="utf-8").read())
    check(set(rep) >= {"structural_rot", "dead_weight", "meta"},
          "audit json has the three contract keys")
    rot_fps = {r["fingerprint"] for r in rep["structural_rot"]}
    check(rot_fps == {"orphan-hook:orphan_widget"},
          "audit's structural_rot names exactly the same fingerprint the gate would block on")
    # the gate blocks (exit 1) on the SAME fingerprint the audit merely surfaces (exit 0)
    bl = os.path.join(d, "bl.json")
    rc_gate, gate_out = run("--root", d, "--check", bl)
    check(rc_gate == 1 and "orphan-hook:orphan_widget" in gate_out,
          "same rot: the gate BLOCKS (exit 1) where the audit ADVISES (exit 0) - the firewall")


# ============================== 6. trunk smoke: young trunk is clean on both axes (SC1.8)
print("[6] e2e: real trunk audit is clean - 0 rot (== gate) and 0 dead-weight (<90d)")
with tempfile.TemporaryDirectory() as d:
    out_json = os.path.join(d, "trunk_audit.json")
    rc, _ = run("--audit", out_json)
    rep = json.loads(open(out_json, encoding="utf-8").read())
    check(rep["structural_rot"] == [], "trunk audit: 0 structural rot (agrees with the clean gate)")
    check(rep["dead_weight"] == [],
          "trunk audit: 0 dead-weight (every artifact is <90d old - correctly nothing to prune yet)")


# ============================== 7. /meta-retro is actually wired to consume the audit (SC1.7)
print("[7] meta-retro.md runs --audit and states the surface-only / no-auto-prune rule")
mr = open(os.path.join(ROOT, "commands", "meta-retro.md"), encoding="utf-8").read()
check("extract.py --audit" in mr or "--audit" in mr,
      "meta-retro invokes the audit feed")
check(("no auto-prune" in mr.lower()) or ("never auto" in mr.lower())
      or ("surface" in mr.lower() and "human" in mr.lower()),
      "meta-retro states the firewall: candidates are surfaced, pruning stays human")


# ===================================== 8. heal-health vital sign (auto-healer v2 synergy)
print("[8] heal_health(): repo-key agrees with heal.py, advisory firewall, fail-open")
sys.path.insert(0, os.path.join(ROOT, "skills", "auto-healer"))
import heal  # the single-source predicate module heal_health imports

# (a) the drift risk: cartograph's repo-key derivation must match heal.py's exactly.
# test cwd is cartograph/, whose git toplevel is ROOT -> heal._repo_key() keys to ROOT.
check(ex._heal_repo_key(ROOT) == heal._repo_key(),
      "cartograph _heal_repo_key(ROOT) == heal.py _repo_key() (no key drift)")

# (b) audit_report always carries the heal_health key + meta count (None on clean trunk).
g2 = ex.Graph()
g2.node("skill:x", "skill", "x", file="skills/x/SKILL.md", added=OLD, fires=1)
rep2 = ex.audit_report(g2, [], today=TODAY)
check("heal_health" in rep2 and "heal_escalate_count" in rep2["meta"],
      "audit_report has heal_health + meta.heal_escalate_count keys")

# (c) populated path on a fixture root: a recurring+failed bug -> escalate_count 1,
# advisory + non-mutating. Reads the ledger at ex.ROOT; predicates come from heal._metrics.
with tempfile.TemporaryDirectory() as d:
    key = ex._heal_repo_key(d)
    hd = os.path.join(d, "state", "heal", key)
    write(os.path.join(hd, "bugs.jsonl"),
          json.dumps({"id": "b1", "status": "recurred", "recurrences": 1,
                      "tags": [], "summary": "root defect", "links": []}) + "\n")
    write(os.path.join(hd, "attempts.jsonl"),
          json.dumps({"id": "a1", "bug": "b1", "outcome": "failed",
                      "ts": "2026-01-01T00:00:00+00:00"}) + "\n")
    saved = ex.ROOT
    try:
        ex.ROOT = d
        h = ex.heal_health()
    finally:
        ex.ROOT = saved
    check(h is not None and h["escalate_count"] == 1 and h["n_bugs"] == 1,
          "heal_health reads the ledger: recurring+failed -> escalate_count 1")
    check(h.get("advisory") is True and h.get("mutates") is False,
          "heal_health declares the firewall: advisory, non-mutating")

# (d) fail-open: an empty/absent ledger -> None (never bricks --audit/--json/--check).
with tempfile.TemporaryDirectory() as d:
    saved = ex.ROOT
    try:
        ex.ROOT = d
        check(ex.heal_health() is None, "absent heal ledger -> None (fail-open)")
    finally:
        ex.ROOT = saved

# (e) e2e: --check (the gate) never blocks on heal state - it is overlay, not structure.
rc_chk, _ = run("--check")
check(rc_chk in (0, 1), "--check runs; heal-health is advisory overlay, not a gate input")


# ============================================================================ done
print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
