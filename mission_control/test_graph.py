#!/usr/bin/env python3
"""Tests for Mission Control P2 - the Graph (Map) lens + selection-follow across lenses.

Same runner style as test_smoke.py: two tiers.
  [1] data firewall - pure logic, runs WITHOUT textual. UNIT (pinned cases) + PROPERTY
      (invariants over randomized payloads, derived from the lens's INTENT, authored RED).
  [2] textual pilot - mounts the app headless, asserts the Map lens renders loop groups and
      that selection FOLLOWS the component across the Roster<->Map lens switch (one model).
      SKIPPED (not failed) if textual is absent.

P2 SUCCESS CRITERIA (inline; `extract.py --query governed-by mission_control/app.py` => MISS,
so no governing spec - criteria live here):

  C1 ADJACENCY IS THE EDGE SET, NOTHING MORE. `adjacency(payload)` derives, per node id, its
     out-neighbours (edges where it is `source`) and in-neighbours (edges where it is `target`)
     from `structure.edges` ONLY - no edge invented, none dropped. Conservation: sum of out-degrees
     == sum of in-degrees == edge count. Closure: every edge {s->t} has t in out[s] and s in in[t].
  C2 MAP NODES = COMPONENT NODES, GAUGED BY THE SHARED WORK MODEL. `graph_nodes(payload)` returns
     exactly the component nodes (a real `file`, not `missing`); each carries loop/type/label and a
     `state` derived by the SAME _derive_state the Roster lanes use. A node with no work is NOMINAL.
  C3 ONE MODEL, TWO FACES (the load-bearing intent). For any component that is BOTH a Map node and
     a Roster lane, the two lenses report the SAME state. Falsification = the lenses disagree, i.e.
     "selection follows across lenses on one model" is a lie.
  C4 LOOPS PARTITION THE NODES. `graph_by_loop(payload)` buckets every Map node into exactly one
     loop group (none dropped, none duplicated); a node with no loop lands in a named bucket, never
     vanishes.
  C5 HONEST DEGRADATION. An empty payload yields empty adjacency/graph_nodes/loops - never a
     fabricated node or edge (the same contract --mission and the lanes keep). A dangling edge
     endpoint (target not among nodes) is handled without a traceback.
  C6 SELECTION FOLLOWS ACROSS LENSES (behavioural). The app keys selection on a component id, not a
     row index; switching Roster<->Map preserves the selected component, and the detail bay renders
     it in either lens.

Run:  python mission_control/test_graph.py      # exits non-zero on any failure
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # repo root on path -> `import mission_control` works

from mission_control import data
from mission_control.data import (
    STATE_ACTIVE, STATE_BLOCKED, STATE_NOMINAL, STATE_PROPOSED,
    component_lanes,
)

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


# ── a small, deterministic payload with the cross-lens overlap the intent needs ──────────────
# 6 component nodes across 3 loops + 1 NON-component (session, no file) that must be excluded from
# the Map. Work overlaps three of them: alpha BLOCKED, gamma ACTIVE, delta PROPOSED. beta/epsilon/
# zeta carry no work => NOMINAL. 5 edges (one a born_in lineage edge to the session).
def _node(nid, typ, loop, file):
    return {"id": nid, "type": typ, "label": nid.split(":", 1)[-1], "loop": loop, "file": file}


GRAPH_NODES = [
    _node("skill:alpha", "skill", "core", "skills/alpha/SKILL.md"),
    _node("skill:beta", "skill", "core", "skills/beta/SKILL.md"),
    _node("skill:zeta", "skill", "core", "skills/zeta/SKILL.md"),
    _node("command:gamma", "command", "support", "commands/gamma.md"),
    _node("agent:delta", "agent", "support", "agents/delta.md"),
    _node("hook:epsilon", "hook", "meta", "hooks/epsilon.py"),
    {"id": "session:s1", "type": "session", "label": "s1", "loop": None, "file": None},  # excluded
]
GRAPH_EDGES = [
    {"source": "skill:alpha", "target": "command:gamma", "type": "invokes"},
    {"source": "skill:beta", "target": "skill:alpha", "type": "cites"},
    {"source": "command:gamma", "target": "agent:delta", "type": "spawns"},
    {"source": "hook:epsilon", "target": "skill:alpha", "type": "nudges"},
    {"source": "skill:alpha", "target": "session:s1", "type": "born_in"},
]


def _comp(nid, typ, file):
    return {"id": nid, "type": typ, "file": file}


def make_payload():
    return {
        "structure": {
            "nodes": [dict(n) for n in GRAPH_NODES],
            "edges": [dict(e) for e in GRAPH_EDGES],
            "node_count": len(GRAPH_NODES),
            "edge_count": len(GRAPH_EDGES),
        },
        "work": {
            "by_component": {
                "skill:alpha": {
                    "component": _comp("skill:alpha", "skill", "skills/alpha/SKILL.md"),
                    "followups": [{"id": "a1", "text": "alpha is blocked on the lease", "task": "", "ts": 1}],
                },
                "command:gamma": {
                    "component": _comp("command:gamma", "command", "commands/gamma.md"),
                    "followups": [{"id": "g1", "text": "gamma open work item", "task": "", "ts": 2}],
                },
                "agent:delta": {
                    "component": _comp("agent:delta", "agent", "agents/delta.md"),
                    "proposals": ["proposals/2026-01-01-delta.md"],
                },
            },
            "unscoped": {"followups": []},
            "proposals": [{"path": "proposals/2026-01-01-delta.md", "name": "delta",
                           "status": "DRAFT", "concerns": ["agent:delta"]}],
            "followups_open": 2,
            "in_flight": {"branch": "main", "session_owner": "de0e3d65", "active_sessions": 1,
                          "trunk_lease_holders": []},
        },
        "health": {"predictions": {"hit_rate": 0.8, "total": 10, "unscored": 0},
                   "corrections_total": 3, "structural_rot": 0,
                   "eval_cases": {"total": 7, "present": 7}},
        "meta": {"view": "mission", "node_count": len(GRAPH_NODES), "edge_count": len(GRAPH_EDGES)},
    }


# ════════════════════════════════════════════════════ [1] DATA: adjacency / graph_nodes / loops
def test_adjacency_units():
    print("[1a] adjacency: out/in neighbour sets are the edge set, nothing invented (C1)")
    p = make_payload()
    adj = data.adjacency(p)
    check(adj["skill:alpha"]["out"].count("command:gamma") == 1
          and "session:s1" in adj["skill:alpha"]["out"],
          "alpha's out-neighbours include its real edge targets")
    check("skill:beta" in adj["skill:alpha"]["in"] and "hook:epsilon" in adj["skill:alpha"]["in"],
          "alpha's in-neighbours include the nodes that point at it")
    check(adj["skill:zeta"]["out"] == [] and adj["skill:zeta"]["in"] == [],
          "an isolated node has empty in/out (no fabricated edge)")
    # conservation: every edge contributes exactly one out and one in
    total_out = sum(len(v["out"]) for v in adj.values())
    total_in = sum(len(v["in"]) for v in adj.values())
    check(total_out == len(GRAPH_EDGES) == total_in,
          f"sum(out) == sum(in) == edge count ({len(GRAPH_EDGES)})")


def test_graph_nodes_units():
    print("[1b] graph_nodes: component nodes only, gauged by the shared work model (C2)")
    p = make_payload()
    gn = {n.nid: n for n in data.graph_nodes(p)}
    check("session:s1" not in gn, "a node with no file (session) is excluded from the Map")
    check(set(gn) == {"skill:alpha", "skill:beta", "skill:zeta",
                      "command:gamma", "agent:delta", "hook:epsilon"},
          "exactly the 6 component nodes appear")
    check(gn["skill:alpha"].state == STATE_BLOCKED, "alpha (blocked followup) -> BLOCKED")
    check(gn["command:gamma"].state == STATE_ACTIVE, "gamma (open followup) -> ACTIVE")
    check(gn["agent:delta"].state == STATE_PROPOSED, "delta (proposal only) -> PROPOSED")
    check(gn["skill:beta"].state == STATE_NOMINAL, "beta (no work) -> NOMINAL")
    check(gn["skill:alpha"].out_deg >= 2 and gn["skill:alpha"].in_deg == 2,
          "node carries its degree (out/in counts) from adjacency")
    check(gn["skill:alpha"].loop == "core" and gn["command:gamma"].loop == "support",
          "node carries its loop")


def test_loops_partition_units():
    print("[1c] graph_by_loop: every Map node lands in exactly one loop group (C4)")
    p = make_payload()
    groups = data.graph_by_loop(p)
    loops = [g[0] for g in groups]
    check(set(loops) == {"core", "support", "meta"}, "the three loops are the groups")
    flat = [n.nid for _, members in groups for n in members]
    check(sorted(flat) == sorted(n.nid for n in data.graph_nodes(p)),
          "flattening the loop groups returns every Map node, once (partition: no drop, no dup)")


def test_degradation_units():
    print("[1d] honest degradation: empty/dangling payloads never fabricate or crash (C5)")
    check(data.adjacency({}) == {}, "empty payload -> empty adjacency")
    check(data.graph_nodes({}) == [], "empty payload -> no Map nodes")
    check(data.graph_by_loop({}) == [], "empty payload -> no loop groups")
    # a dangling edge endpoint (target not among nodes) must not raise, and the CONTRACT is pinned:
    # adjacency is keyed by nodes UNION edge-endpoints, so conservation+closure stay TOTAL - the
    # dangling target gets its own key recording who points at it, but is NOT fabricated onto the Map.
    dangling = make_payload()
    dangling["structure"]["edges"].append({"source": "skill:alpha", "target": "ghost:x", "type": "cites"})
    try:
        adj = data.adjacency(dangling)
        out_ok = "ghost:x" in adj.get("skill:alpha", {}).get("out", [])
        closure_ok = "skill:alpha" in adj.get("ghost:x", {}).get("in", [])
        excluded = "ghost:x" not in {n.nid for n in data.graph_nodes(dangling)}
    except Exception:
        out_ok = closure_ok = excluded = False
    check(out_ok, "a dangling edge target appears in its source's out-list (no traceback)")
    check(closure_ok, "closure is total: the dangling target is keyed with its in-edge (nodes U endpoints)")
    check(excluded, "but the dangling endpoint is NOT a Map node (no file) - not fabricated onto the Map")


# ════════════════════════════════════════════════════════════════════════ [1*] PROPERTY tests
# Bounded, SEEDED loop over randomized in-domain payloads. Each property is derived from an INTENT
# clause and would go red on a real "green-but-wrong" build, not on a restatement of the code.
def _rand_payload(rng):
    """A random IN-DOMAIN mission payload: unique node ids (some component, some not), edges only
    between existing nodes, work folded onto a random subset of component nodes."""
    n = rng.randint(0, 12)
    nodes, comp_ids = [], []
    loops = ["core", "support", "meta", None]
    for i in range(n):
        nid = f"skill:n{i}"
        has_file = rng.random() < 0.7
        f = f"skills/n{i}/SKILL.md" if has_file else None
        nd = _node(nid, "skill", rng.choice(loops), f)
        if not has_file:
            nd["file"] = None
        nodes.append(nd)
        if has_file:
            comp_ids.append(nid)
    ids = [x["id"] for x in nodes]
    edges = []
    if ids:
        for _ in range(rng.randint(0, 15)):
            # ~20% of edges dangle to a non-existent target, exercising closure/conservation TOTALITY
            tgt = f"ghost:{rng.randint(0, 99)}" if rng.random() < 0.2 else rng.choice(ids)
            edges.append({"source": rng.choice(ids), "target": tgt,
                          "type": rng.choice(["cites", "invokes", "nudges", "born_in"])})
    by_comp = {}
    for nid in comp_ids:
        roll = rng.random()
        comp = _comp(nid, "skill", dict((x["id"], x) for x in nodes)[nid]["file"])
        if roll < 0.25:
            by_comp[nid] = {"component": comp,
                            "followups": [{"id": "x", "text": "this is blocked", "task": "", "ts": 0}]}
        elif roll < 0.5:
            by_comp[nid] = {"component": comp,
                            "followups": [{"id": "x", "text": "open item", "task": "", "ts": 0}]}
        elif roll < 0.7:
            by_comp[nid] = {"component": comp, "proposals": [f"proposals/{nid}.md"]}
    return {
        "structure": {"nodes": nodes, "edges": edges,
                      "node_count": len(nodes), "edge_count": len(edges)},
        "work": {"by_component": by_comp, "unscoped": {"followups": []}, "proposals": [],
                 "followups_open": 0, "in_flight": {}},
        "health": {}, "meta": {"view": "mission"},
    }


def test_properties():
    print("[1p] properties over 300 randomized in-domain payloads (intent invariants)")
    rng = random.Random(20260623)
    bad_conservation = bad_closure = bad_state_dom = bad_cross = bad_partition = bad_excl = 0
    for _ in range(300):
        p = _rand_payload(rng)
        edges = p["structure"]["edges"]
        adj = data.adjacency(p)
        # C1 conservation: would catch an edge dropped or double-counted
        if not (sum(len(v["out"]) for v in adj.values()) == len(edges)
                == sum(len(v["in"]) for v in adj.values())):
            bad_conservation += 1
        # C1 closure: would catch an edge reflected on the wrong endpoint
        for e in edges:
            if e["target"] not in adj.get(e["source"], {}).get("out", []) \
               or e["source"] not in adj.get(e["target"], {}).get("in", []):
                bad_closure += 1
                break
        gn = data.graph_nodes(p)
        # C2 state domain: would catch a bogus/empty state slipping through
        if any(g.state not in (STATE_ACTIVE, STATE_BLOCKED, STATE_PROPOSED, STATE_NOMINAL) for g in gn):
            bad_state_dom += 1
        # C2 exclusion: would catch a non-component node leaking onto the Map
        comp_ids = {x["id"] for x in p["structure"]["nodes"] if x.get("file")}
        if {g.nid for g in gn} != comp_ids:
            bad_excl += 1
        # C3 ONE MODEL: a node that is both a lane and a Map node must report the SAME state
        lanes = {l.nid: l.state for l in component_lanes(p)}
        for g in gn:
            if g.nid in lanes and lanes[g.nid] != g.state:
                bad_cross += 1
                break
        # C4 partition: loop groups cover every Map node exactly once
        flat = [m.nid for _, members in data.graph_by_loop(p) for m in members]
        if sorted(flat) != sorted(g.nid for g in gn) or len(flat) != len(set(flat)):
            bad_partition += 1
    check(bad_conservation == 0, "P-C1a edge conservation holds on every random payload")
    check(bad_closure == 0, "P-C1b edge closure holds (each edge on the right endpoints)")
    check(bad_state_dom == 0, "P-C2a every Map node's state is one of the 4 gauge states")
    check(bad_excl == 0, "P-C2b Map nodes are EXACTLY the component (file-backed) nodes")
    check(bad_cross == 0, "P-C3 lane state == Map state for every shared component (ONE MODEL)")
    check(bad_partition == 0, "P-C4 loop groups partition the Map nodes (no drop, no dup)")


# ═══════════════════════════════════════════════════════════════════ [2] textual pilot (C6)
async def _pilot():
    from textual.widgets import Static
    from mission_control.app import MissionControl
    payload = make_payload()
    app = MissionControl(lambda: payload, name_label="MISSION CONTROL", channel="01")
    async with app.run_test() as pilot:
        await pilot.pause()
        # default lens is the Roster; selection keys on a component id, not a row index
        check(app.lens == "roster", "app opens on the Roster lens")
        check(app.selected_nid == app.lanes[0].nid, "selection starts on the first lane's component id")
        first = app.selected_nid

        # switch to the Map lens; the SAME component stays selected (selection-follow, one model)
        while app.lens != "map":
            await pilot.press("tab")
            await pilot.pause()
        gnodes = list(app.query(".gnode"))
        check(len(gnodes) == 6, f"Map lens mounts the 6 component nodes (got {len(gnodes)})")
        check(app.selected_nid == first, "switching Roster->Map preserved the selected component")
        detail_map = str(app.query_one("#detail-body", Static).render())
        check(first.split(":", 1)[-1].upper() in detail_map.upper(),
              "the detail bay renders the selected component in the Map lens")

        # the lens's DEFINING contract: node state is rendered BY STROKE, not ignored at render time.
        # A Map that mounts 6 identically-painted widgets would pass len()==6 but fail HERE.
        by_nid = {w.node.nid: w for w in gnodes}
        m_blocked = str(by_nid["skill:alpha"].render())   # BLOCKED component
        m_nominal = str(by_nid["skill:beta"].render())    # NOMINAL component
        check("▮" in m_blocked, "the blocked Map node renders the fault stroke glyph")
        check("▮" not in m_nominal and m_blocked != m_nominal,
              "node state IS rendered by stroke (blocked stroke != nominal stroke)")
        blk_styles = " ".join(str(s.style) for s in by_nid["skill:alpha"].render().spans).lower()
        check("e2503a" in blk_styles, "the blocked node carries the --fault color token in its markup")

        # Map node order is DETERMINISTIC across reads, so cursor traversal is stable, not arbitrary
        order1 = [n.nid for n in data.graph_nodes(payload)]
        order2 = [n.nid for n in data.graph_nodes(payload)]
        check(order1 == order2 and len(order1) == 6, "Map node order is stable across reads")

        # move the cursor in the Map: selection moves to a KNOWN component (pins WHERE, not just that
        # selected_nid changed to anything) + detail follows
        await pilot.press("down")
        await pilot.pause()
        known = {"skill:alpha", "skill:beta", "skill:zeta",
                 "command:gamma", "agent:delta", "hook:epsilon"}
        check(app.selected_nid != first and app.selected_nid in known,
              "down moves the Map selection to another KNOWN component")
        moved = app.selected_nid

        # switch back to the Roster: the component selected in the Map is STILL selected
        while app.lens != "roster":
            await pilot.press("tab")
            await pilot.pause()
        check(app.selected_nid == moved, "switching Map->Roster preserved the Map-selected component")


# ════════════════════════════ [2b] selection-follow EDGE cases (off-lens + reload preserve)
# A component can be a Roster lane (carries work) yet have NO Map node (no structure node / no file).
# Two contracts: (1) reload/sort PRESERVES the selected component; (2) switching to a lens that does
# NOT contain it snaps the cursor to a visible row (the lens never renders cursorless).
async def _pilot_edge():
    from textual.widgets import Static
    from mission_control.app import MissionControl
    payload = {
        "structure": {"nodes": [
            _node("skill:a", "skill", "core", "skills/a/SKILL.md"),
            _node("skill:b", "skill", "core", "skills/b/SKILL.md"),
        ], "edges": [], "node_count": 2, "edge_count": 2},
        "work": {"by_component": {
            "skill:a": {"component": _comp("skill:a", "skill", "skills/a/SKILL.md"),
                        "followups": [{"id": "a1", "text": "a is blocked", "task": "", "ts": 1}]},
            # a Roster-only component: carries work but has NO structure node -> not a Map node
            "skill:ghost": {"component": _comp("skill:ghost", "skill", "skills/ghost/SKILL.md"),
                            "followups": [{"id": "g1", "text": "ghost open work", "task": "", "ts": 2}]},
        }, "unscoped": {"followups": []}, "proposals": [], "followups_open": 2, "in_flight": {}},
        "health": {}, "meta": {"view": "mission"},
    }
    app = MissionControl(lambda: payload, name_label="MC", channel="01")
    async with app.run_test() as pilot:
        await pilot.pause()
        # move selection onto the Roster-only component
        while app.selected_nid != "skill:ghost":
            await pilot.press("down")
            await pilot.pause()
        check(app.selected_nid == "skill:ghost", "selected the Roster-only component (skill:ghost)")

        # (1) reload PRESERVES the selected component (it must not snap back to row 0)
        await pilot.press("r")
        await pilot.pause()
        check(app.selected_nid == "skill:ghost", "reload preserves the selected component (not row 0)")

        # (2) one model: switch to the Map (which has NO ghost node). selected_nid PERSISTS (a lens
        # switch never mutates it), the Map shows no cursor for it, but the detail bay still shows it.
        while app.lens != "map":
            await pilot.press("tab")
            await pilot.pause()
        check(app.selected_nid == "skill:ghost",
              "selection PERSISTS into a lens that lacks the component (not mutated)")
        check(len([w for w in app.query(".gnode") if w.has_class("-selected")]) == 0,
              "the Map shows no cursor for a component it does not contain (honest, not snapped)")
        check("GHOST" in str(app.query_one("#detail-body", Static).render()).upper(),
              "the detail bay still shows the off-lens selected component")

        # (3) tab back to a lens that HAS it -> re-highlighted (the round-trip the one-model needs)
        while app.lens != "roster":
            await pilot.press("tab")
            await pilot.pause()
        check(app.selected_nid == "skill:ghost", "round-trip through a lacking lens preserved selection")
        sel = [w for w in app.query(".lane") if w.has_class("-selected")]
        check(len(sel) == 1 and sel[0].nid == "skill:ghost", "ghost is re-highlighted on return to Roster")

        # (4) cursor nav re-engages a real row from a cursorless lens (the recovery path)
        while app.lens != "map":
            await pilot.press("tab")
            await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        check(app.selected_nid in {"skill:a", "skill:b"},
              "down from a cursorless Map engages a real Map node")


def test_edge_cases():
    print("[2b] selection-follow edge cases: reload-preserve + off-lens cursor snap")
    try:
        import textual  # noqa: F401
    except ImportError:
        print("  skip (textual not installed)")
        return
    import asyncio
    asyncio.run(_pilot_edge())


def test_tui():
    print("[2] textual pilot: Map lens renders loop groups + selection follows across lenses (C6)")
    try:
        import textual  # noqa: F401
    except ImportError:
        print("  skip (textual not installed) - pip install textual to run the TUI tier")
        return
    import asyncio
    asyncio.run(_pilot())


if __name__ == "__main__":
    # wrap each group so a missing attribute in one does not hide the RED picture of the others
    for fn in (test_adjacency_units, test_graph_nodes_units, test_loops_partition_units,
               test_degradation_units, test_properties, test_edge_cases, test_tui):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - test-first: missing-attr is the expected RED
            _failed += 1
            print(f"  FAIL {fn.__name__} raised {type(exc).__name__}: {exc}")
    print(f"\n{_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)
