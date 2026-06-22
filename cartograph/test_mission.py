#!/usr/bin/env python3
"""Tests for Mission Control P0 - the read-only `extract.py --mission` data layer.

--mission emits ONE unified JSON payload that JOINS three layers onto the existing component
nodes, keyed by file path: structure (the graph cartograph already extracts) + work (open
followups & proposals folded by the component they concern, plus git in-flight) + health
(calibration/corrections/eval summary, reusing compute_overlay). Its load-bearing contract is
ADDITIVE + READ-ONLY: the join lives entirely in the payload (a `concerns` association is a
payload field, never a g.edge), so it introduces NO node, NO edge, and NO new relation type -
in-degree / dependents / blast-radius / orphans / the gate must be byte-for-byte identical to a
run without --mission. These tests pin that firewall down, plus the join itself (a known followup
/ proposal lands on the right component; the unscoped bucket works; structure counts unchanged).

Self-contained, same runner style as test_query.py / test_audit.py: pure-logic units run
in-process on synthetic graphs + throwaway --root fixtures (so the join is asserted without
depending on the real, gitignored state/ ledgers); the e2e cases drive the CLI on the real trunk
and assert valid JSON + read-only.

Run:  python cartograph/test_mission.py      # exits non-zero on any failure
"""
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
    return r.returncode, r.stdout, r.stderr


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def S(seq):
    return sorted(seq)


# ===================================================== 0. the ADDITIVE/READ-ONLY firewall
# The whole hard-rule of P0: --mission must not perturb the graph's nodes, edges, or relation
# types. Assert the negative directly so a future leak (e.g. a `concerns` edge into g.edges, or a
# new type into REF/DEP) is caught, not silently absorbed.
print("[0] additive firewall: --mission introduces no node/edge/relation into the graph math")
check("concerns" not in getattr(ex, "REF_EDGE_TYPES", set()),
      "no `concerns` (or any mission relation) leaked into REF_EDGE_TYPES (in-degree/orphan math)")
check("concerns" not in getattr(ex, "DEP_EDGE_TYPES", set()),
      "no mission relation leaked into DEP_EDGE_TYPES (blast-radius/dependents math)")
# the edge-type universe the extractor can ever emit - mission adds none of its own
_KNOWN_EDGE_TYPES = {"fires_on", "born_in", "cites", "invokes", "spawns", "references",
                     "touches", "wires", "nudges", "specifies", "requires", "verified_by"}
_g0, _w0, _n0, _wired0 = ex.build()
check({e["type"] for e in _g0.edges} <= _KNOWN_EDGE_TYPES,
      "the built graph emits only the known edge types - mission adds no edge type")
_payload0 = ex.build_mission_payload(_g0, ex.compute_overlay(_g0), _w0, _n0, {})
check({e["type"] for e in _payload0["structure"]["edges"]} <= _KNOWN_EDGE_TYPES,
      "the mission payload's structure edges are exactly the graph's - no `concerns` edge added")


# ===================================================== 1. structure layer == the graph, unchanged
print("[1] structure layer reuses the extracted graph as-is (counts identical to a plain build)")
g1, w1, n1, _wired1 = ex.build()
plain_nodes, plain_edges = len(g1.nodes), len(g1.edges)
ov1 = ex.compute_overlay(g1)
p1 = ex.build_mission_payload(g1, ov1, w1, n1, {})
check(p1["structure"]["node_count"] == plain_nodes,
      f"structure.node_count == plain build node count ({plain_nodes})")
check(p1["structure"]["edge_count"] == plain_edges,
      f"structure.edge_count == plain build edge count ({plain_edges})")
check(len(p1["structure"]["nodes"]) == plain_nodes and len(p1["structure"]["edges"]) == plain_edges,
      "structure.nodes / .edges lists are the graph's own, same length")
check(S(p1.keys()) == ["health", "meta", "structure", "work"],
      "top-level payload shape = {structure, work, health, meta}")
check(p1["meta"].get("view") == "mission", "meta.view tags this as the mission payload")


# ===================================================== 2. proposal_status: bold bullet, not YAML
print("[2] proposal_status() reads the `- **Status:** X` bullet, never the YAML status: key")
check(ex.proposal_status("- **Status:** DRAFT / for human approval. Nothing built.") == "DRAFT",
      "leading state word of the bold-bullet status is extracted")
check(ex.proposal_status("- **Status:** PROPOSAL - converging.") == "PROPOSAL",
      "an em/en-dash-or-hyphen-terminated status word is split cleanly")
check(ex.proposal_status("body text only, no status line") == "",
      "no status bullet -> empty string (not a guess)")
check(ex.proposal_status("```\nstatus: proposed|building|shipped\n```\n") == "",
      "a code-fence YAML status: line is NOT read as the doc's status (anti-false-read)")
# a doc with BOTH (the real SDD proposal shape) must pick the bullet
both = "- **Status:** PROPOSAL - design settled.\n\n```\nstatus: shipped\n```\n"
check(ex.proposal_status(both) == "PROPOSAL", "with both forms present, the bold bullet wins")


# ===================================================== 3. e2e join: followup -> right component
# Build a throwaway harness via --root with ONE skill and ONE followup whose text names that
# skill's file path. The followup must fold onto that component; nothing must go unscoped.
print("[3] e2e join: a followup naming a component's file lands on that component")
with tempfile.TemporaryDirectory() as d:
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "skills", "widget", "SKILL.md"),
          "---\nname: widget\n---\nThe widget procedure.\n")
    write(os.path.join(d, "state", "followups.jsonl"),
          json.dumps({"id": "aa1", "text": "fix skills/widget/SKILL.md typo",
                      "task": "", "status": "open"}) + "\n")
    rc, out, err = run("--root", d, "--mission")
    check(rc == 0, f"--mission on a fixture exits 0 (got {rc})")
    j = json.loads(out)
    bc = j["work"]["by_component"]
    check("skill:widget" in bc, "the followup folded onto skill:widget (by file-path mention)")
    ids = [f["id"] for f in bc.get("skill:widget", {}).get("followups", [])]
    check(ids == ["aa1"], "the right followup id is attached to the component")
    check(j["work"]["followups_open"] == 1, "open followup count is 1")
    check(j["work"]["unscoped"]["followups"] == [],
          "the associated followup is NOT also in the unscoped bucket")


# ===================================================== 4. e2e: unscoped bucket (no association)
print("[4] e2e: a followup that names no component goes to the unscoped bucket, not fabricated")
with tempfile.TemporaryDirectory() as d:
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "skills", "widget", "SKILL.md"),
          "---\nname: widget\n---\nThe widget procedure.\n")
    write(os.path.join(d, "state", "followups.jsonl"),
          json.dumps({"id": "bb2", "text": "buy more coffee for the office",
                      "task": "", "status": "open"}) + "\n")
    rc, out, err = run("--root", d, "--mission")
    j = json.loads(out)
    unscoped_ids = [f["id"] for f in j["work"]["unscoped"]["followups"]]
    check(unscoped_ids == ["bb2"], "the unassociable followup is in the unscoped bucket")
    check("skill:widget" not in j["work"]["by_component"],
          "no component was fabricated for the unrelated followup")
    check(j["work"]["followups_open"] == 1, "it still counts toward followups_open")


# ===================================================== 5. e2e: a `done` followup is excluded
print("[5] e2e: only OPEN followups are folded; done ones are skipped entirely")
with tempfile.TemporaryDirectory() as d:
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "skills", "widget", "SKILL.md"),
          "---\nname: widget\n---\nThe widget procedure.\n")
    write(os.path.join(d, "state", "followups.jsonl"),
          json.dumps({"id": "cc3", "text": "skills/widget/SKILL.md done item",
                      "task": "", "status": "done"}) + "\n")
    rc, out, err = run("--root", d, "--mission")
    j = json.loads(out)
    check(j["work"]["followups_open"] == 0, "a done followup is not counted as open")
    check("skill:widget" not in j["work"]["by_component"]
          and j["work"]["unscoped"]["followups"] == [],
          "a done followup appears in neither the component nor the unscoped bucket")


# ===================================================== 6. e2e: proposal Status + association
print("[6] e2e: a proposal's Status is parsed and it folds onto the component it names")
with tempfile.TemporaryDirectory() as d:
    write(os.path.join(d, "settings.json"), '{"hooks": {}}')
    write(os.path.join(d, "skills", "widget", "SKILL.md"),
          "---\nname: widget\n---\nThe widget procedure.\n")
    write(os.path.join(d, "proposals", "2026-01-01-widget-rework.md"),
          "# Proposal\n\n- **Status:** DRAFT / for approval.\n\n"
          "Reworks skills/widget/SKILL.md substantially.\n")
    rc, out, err = run("--root", d, "--mission")
    j = json.loads(out)
    props = {p["name"]: p for p in j["work"]["proposals"]}
    check("2026-01-01-widget-rework" in props, "the proposal is listed in work.proposals")
    check(props["2026-01-01-widget-rework"]["status"] == "DRAFT",
          "the proposal's Status was parsed from its bold bullet")
    check("skill:widget" in props["2026-01-01-widget-rework"]["concerns"],
          "the proposal concerns the component whose file it names")
    bc = j["work"]["by_component"].get("skill:widget", {})
    check(any("widget-rework" in p for p in bc.get("proposals", [])),
          "the proposal is folded under the component in by_component")


# ===================================================== 7. e2e: git in-flight + health shape
print("[7] e2e: in_flight carries the git branch; health reuses the overlay summary")
rc, out, err = run("--mission")
check(rc == 0, f"--mission on the real trunk exits 0 (got {rc})")
j = json.loads(out)
check("branch" in j["work"]["in_flight"], "in_flight reports the current git branch")
h = j["health"]
check("predictions" in h and "corrections_total" in h and "structural_rot" in h,
      "health carries predictions + corrections_total + structural_rot (reused overlay)")
check(h["structural_rot"] == len(w1),
      "health.structural_rot equals the gate's warning count (same source of truth)")
check(isinstance(j["work"]["proposals"], list) and len(j["work"]["proposals"]) >= 1,
      "the real trunk's proposals/ are surfaced as work items")


# ===================================================== 8. e2e: --mission emits VALID JSON only
print("[8] e2e: --mission prints valid JSON to stdout and nothing but JSON")
rc, out, err = run("--mission")
try:
    json.loads(out)
    valid = True
except Exception:
    valid = False
check(valid, "stdout parses as a single JSON document")
check(out.lstrip().startswith("{"), "stdout starts with a JSON object (no text-dump prefix)")


# ===================================================== 9. e2e: --mission is READ-ONLY
print("[9] e2e: --mission mutates nothing (git porcelain + index.html unchanged)")
html = os.path.join(HERE, "index.html")
before_html = os.path.getmtime(html) if os.path.exists(html) else None
porc_before = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                             capture_output=True, text=True).stdout
run("--mission")
porc_after = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                            capture_output=True, text=True).stdout
after_html = os.path.getmtime(html) if os.path.exists(html) else None
check(porc_before == porc_after, "git porcelain unchanged after --mission (no new/edited files)")
check(before_html == after_html, "index.html not rewritten by --mission")
# the drift-discipline rule: no static mission.json is ever written
check(not os.path.isfile(os.path.join(HERE, "mission.json")),
      "no static cartograph/mission.json is created (computed on demand only)")


# ===================================================== 10. structure counts == plain default run
# The cross-check the task calls out explicitly: a plain run and the mission run must report the
# SAME node/edge counts (the additive guarantee, observed end-to-end through the CLI).
print("[10] e2e: structure counts in --mission match the plain --json default run")
rc, out_json, err = run("--json")
plain = json.loads(out_json)
rc, out_mission, err = run("--mission")
mission = json.loads(out_mission)
check(mission["structure"]["node_count"] == plain["meta"]["node_count"],
      f"node_count matches plain run ({plain['meta']['node_count']})")
check(mission["structure"]["edge_count"] == plain["meta"]["edge_count"],
      f"edge_count matches plain run ({plain['meta']['edge_count']})")


# ============================================================================ done
print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
