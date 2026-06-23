#!/usr/bin/env python3
"""Tests for Mission Control P3 - the Console station: Proof counters + layer toggles.

Two tiers (same runner style as test_graph.py):
  [1] data firewall - pure logic, runs WITHOUT textual. UNIT + PROPERTY.
  [2] textual pilot - the Console lens shows the Proof readouts; the work/health LAYER TOGGLES
      dim their gauges WITHOUT hiding rows; selection still follows across all THREE lenses.

P3 SUCCESS CRITERIA (inline; no governing spec):

  C1 PROOF = LIVE HEALTH AS COUNTERS, HONESTLY. `proof_counters(payload)` projects the harness-wide
     health (calibration hit-rate, eval present/total, prediction total + unscored, corrections) into
     labelled readouts. Every value is best-effort: an ABSENT datum renders "—" with tone "none" -
     never a fabricated 0 (the --mission honesty contract).
  C2 UNSCORED IS DEBT (a gauge with meaning, not decoration). The UNSCORED counter's tone is "warn"
     iff unscored > 0, "ok" at 0; it is the one Proof counter whose colour carries a judgement (the
     kernel calls unscored predictions debt). Pin BOTH sides (fires when >0, silent at 0).
  C3 A LAYER TOGGLE DARKENS A GAUGE, IT DOES NOT HIDE A ROW. Toggling the work layer off keeps the
     SAME rows mounted (none hidden) but darkens their work gauge; toggling it back restores it.
     Same for the health layer over the Proof readouts. Falsification = a toggle that removes rows.
  C4 CONSOLE IS THE THIRD LENS; SELECTION STILL FOLLOWS. tab cycles roster->map->console->roster, and
     the selected component is preserved across the full cycle. The Console shows the Proof panel;
     the other lenses do not.
  C5 HONEST DEGRADATION. An empty payload yields all-dash counters (no fake 0) and does not crash.

Run:  python mission_control/test_console.py
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from mission_control import data

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


def make_payload(hit_rate=0.8, pred_total=10, unscored=2, corrections=3,
                 eval_present=7, eval_total=7):
    health = {}
    if hit_rate is not None or pred_total is not None:
        health["predictions"] = {"hit_rate": hit_rate, "total": pred_total, "unscored": unscored}
    if corrections is not None:
        health["corrections_total"] = corrections
    if eval_total is not None:
        health["eval_cases"] = {"present": eval_present, "total": eval_total}
    health["structural_rot"] = 0
    return {
        "structure": {"nodes": [
            {"id": "skill:alpha", "type": "skill", "label": "alpha", "loop": "core",
             "file": "skills/alpha/SKILL.md"},
            {"id": "command:gamma", "type": "command", "label": "gamma", "loop": "support",
             "file": "commands/gamma.md"},
        ], "edges": [], "node_count": 2, "edge_count": 0},
        "work": {
            "by_component": {
                "skill:alpha": {"component": {"id": "skill:alpha", "type": "skill",
                                              "file": "skills/alpha/SKILL.md"},
                                "followups": [{"id": "a1", "text": "alpha is blocked", "task": "", "ts": 1}]},
                "command:gamma": {"component": {"id": "command:gamma", "type": "command",
                                                "file": "commands/gamma.md"},
                                  "followups": [{"id": "g1", "text": "gamma open item", "task": "", "ts": 2}]},
            },
            "unscoped": {"followups": []}, "proposals": [], "followups_open": 2,
            "in_flight": {"branch": "main", "active_sessions": 1, "trunk_lease_holders": []},
        },
        "health": health,
        "meta": {"view": "mission"},
    }


def _by_key(counters):
    return {c.key: c for c in counters}


# ════════════════════════════════════════════════════════════════════ [1] DATA: proof_counters
def test_proof_units():
    print("[1a] proof_counters: live health -> labelled readouts; absent -> dash, not fake 0 (C1)")
    c = _by_key(data.proof_counters(make_payload()))
    check(c["CAL"].value == "80%", "CAL renders the calibration hit-rate as a percent")
    check(c["EVALS"].value == "7/7", "EVALS renders present/total")
    check(c["PRED"].value == "10", "PRED renders the prediction total")
    check(c["UNSCORED"].value == "2", "UNSCORED renders the unscored count")
    check(c["CORR"].value == "3", "CORR renders the corrections total")
    # honesty: an absent datum is a dash, never a 0
    c2 = _by_key(data.proof_counters(make_payload(hit_rate=None, eval_total=None, corrections=None)))
    check(c2["CAL"].value == "—" and c2["CAL"].tone == "none", "absent calibration -> dash, tone none")
    check(c2["EVALS"].value == "—", "absent eval corpus -> dash, not 0/0")
    check(c2["CORR"].value == "—", "absent corrections -> dash, not 0")
    # PARTIAL datum (the sub-dict is PRESENT but a field is None) must STILL dash - never fabricate a
    # 0 (e.g. `f"{present or 0}/{total}"`). This is the fake-zero hole the whole-dict-absent case misses.
    cp = _by_key(data.proof_counters(make_payload(eval_present=None, eval_total=7, pred_total=None)))
    check(cp["EVALS"].value == "—", "eval present=None with total set -> dash, NOT 0/7 (no fake zero)")
    check(cp["PRED"].value == "—", "pred total=None with the dict present -> dash, NOT 0 (no fake zero)")


def test_unscored_tone_both_sides():
    print("[1b] UNSCORED tone is a JUDGEMENT: warn iff unscored>0, ok at 0 (C2, both sides)")
    warn = _by_key(data.proof_counters(make_payload(unscored=3)))["UNSCORED"]
    ok = _by_key(data.proof_counters(make_payload(unscored=0)))["UNSCORED"]
    check(warn.tone == "warn", "unscored>0 -> tone warn (fires: predictions debt is flagged)")
    check(ok.tone == "ok", "unscored==0 -> tone ok (silent: no false alarm when debt is clear)")


def test_degradation_units():
    print("[1c] honest degradation: empty payload -> all-dash counters, no crash (C5)")
    c = _by_key(data.proof_counters({}))
    check(all(x.value == "—" for x in c.values()), "every counter is a dash on an empty payload")
    check(all(x.tone == "none" for x in c.values()), "every tone is 'none' (no fabricated judgement)")


# ════════════════════════════════════════════════════════════════════════ [1*] PROPERTY tests
def _rand_health(rng):
    def maybe(v):
        return v if rng.random() < 0.8 else None
    preds = None
    if rng.random() < 0.8:
        preds = {"hit_rate": maybe(round(rng.random(), 2)),
                 "total": maybe(rng.randint(0, 200)),
                 "unscored": maybe(rng.randint(0, 20))}
    h = {"structural_rot": rng.randint(0, 5)}
    if preds is not None:
        h["predictions"] = preds
    if rng.random() < 0.8:
        h["corrections_total"] = rng.randint(0, 50)
    if rng.random() < 0.8:
        t = rng.randint(0, 30)
        # present is independently maybe-None, so a PARTIAL eval datum is exercised (fake-zero hole)
        h["eval_cases"] = {"total": maybe(t), "present": maybe(rng.randint(0, t))}
    return {"health": h, "structure": {"nodes": [], "edges": []}, "work": {}, "meta": {}}


def test_properties():
    print("[1p] properties over 300 randomized health payloads (intent invariants)")
    rng = random.Random(20260623)
    bad_dash = bad_tone = bad_unscored = bad_partial = 0
    for _ in range(300):
        p = _rand_health(rng)
        unscored_raw = ((p["health"].get("predictions") or {}).get("unscored"))
        cmap = {c.key: c for c in data.proof_counters(p)}
        # C1 partial/absent -> dash, never a fabricated 0 (EVALS/PRED axes)
        ec = p["health"].get("eval_cases")
        if ec is None or ec.get("present") is None or ec.get("total") is None:
            if cmap["EVALS"].value != "—":
                bad_partial += 1
        preds = p["health"].get("predictions")
        if preds is None or preds.get("total") is None:
            if cmap["PRED"].value != "—":
                bad_partial += 1
        for ctr in data.proof_counters(p):
            # C1: a counter is EITHER a real formatted value with a non-'none' judgement, OR a dash
            # with tone 'none' - never a dash that still claims a tone, never a value with tone none.
            if ctr.value == "—" and ctr.tone != "none":
                bad_dash += 1
            # C2: UNSCORED tone tracks the raw debt, both directions
            if ctr.key == "UNSCORED":
                if unscored_raw is None:
                    if not (ctr.value == "—" and ctr.tone == "none"):
                        bad_unscored += 1
                elif unscored_raw > 0 and ctr.tone != "warn":
                    bad_unscored += 1
                elif unscored_raw == 0 and ctr.tone != "ok":
                    bad_unscored += 1
            # tone domain
            if ctr.tone not in ("ok", "warn", "none"):
                bad_tone += 1
    check(bad_dash == 0, "P-C1 a dash counter always carries tone 'none' (no phantom judgement)")
    check(bad_partial == 0, "P-C1b a partial/absent datum dashes, never a fabricated 0 (EVALS/PRED)")
    check(bad_tone == 0, "P-C* every tone is one of ok/warn/none")
    check(bad_unscored == 0, "P-C2 UNSCORED tone tracks the raw unscored debt on every payload")


# ═══════════════════════════════════════════════════════════════════ [2] textual pilot (C3, C4)
def _span_colors(widget):
    return " ".join(str(s.style) for s in widget.render().spans).lower()


async def _pilot():
    from textual.widgets import Static
    from mission_control.app import MissionControl
    payload = make_payload()
    app = MissionControl(lambda: payload, name_label="MISSION CONTROL", channel="01")
    async with app.run_test() as pilot:
        await pilot.pause()
        start = app.selected_nid

        # C4: tab cycles through THREE lenses, selection preserved across the full cycle
        await pilot.press("tab"); await pilot.pause()
        check(app.lens == "map", "tab 1 -> map")
        await pilot.press("tab"); await pilot.pause()
        check(app.lens == "console", "tab 2 -> console (the third lens)")
        proof = app.query_one("#proof", Static)
        check(proof.display, "the Proof panel is visible in the Console lens")
        proof_txt = str(proof.render())
        check("80%" in proof_txt and "7/7" in proof_txt, "Proof shows live calibration + eval counters")
        await pilot.press("tab"); await pilot.pause()
        check(app.lens == "roster", "tab 3 -> back to roster")
        check(app.selected_nid == start, "selection preserved across the full roster->...->roster cycle")

        # C3: layer toggles DARKEN gauges, never HIDE rows. Go to console (lanes + Proof both live).
        await pilot.press("tab"); await pilot.press("tab"); await pilot.pause()
        check(app.lens == "console", "back in console for the layer-toggle checks")
        lanes_before = list(app.query(".lane"))
        n_before = len(lanes_before)
        blocked_lane = next(w for w in lanes_before if w.nid == "skill:alpha")
        lit = _span_colors(blocked_lane)
        check("e2503a" in lit, "with the work layer lit, the blocked lane shows the fault gauge")

        await pilot.press("w"); await pilot.pause()   # toggle WORK layer off
        lanes_after = list(app.query(".lane"))
        check(len(lanes_after) == n_before, "toggling the work layer off HIDES NO ROWS (same count)")
        dim = _span_colors(next(w for w in lanes_after if w.nid == "skill:alpha"))
        check("e2503a" not in dim, "the work gauge is DARKENED when the work layer is off")
        await pilot.press("w"); await pilot.pause()   # toggle back on
        check("e2503a" in _span_colors(next(w for w in app.query(".lane") if w.nid == "skill:alpha")),
              "toggling the work layer back on RESTORES the gauge")

        # health layer DARKENS the Proof readouts (directional, not just "changed"), rows still present
        proof_lit = _span_colors(app.query_one("#proof", Static))
        check("cdbfa6" in proof_lit or "e2503a" in proof_lit,
              "with the health layer lit, the Proof readouts use value/judgement colors")
        await pilot.press("h"); await pilot.pause()
        proof_dim = _span_colors(app.query_one("#proof", Static))
        check("544c3f" in proof_dim, "the dimmed Proof readouts use the faint token (darkened)")
        check("cdbfa6" not in proof_dim and "e2503a" not in proof_dim,
              "the lit value/judgement colors are GONE when health is off (darkened, not recolored/brightened)")
        check(len(list(app.query(".lane"))) == n_before, "the health toggle hides no lane rows either")


def test_tui():
    print("[2] textual pilot: Console lens + Proof + layer toggles + 3-lens selection-follow")
    try:
        import textual  # noqa: F401
    except ImportError:
        print("  skip (textual not installed)")
        return
    import asyncio
    asyncio.run(_pilot())


if __name__ == "__main__":
    for fn in (test_proof_units, test_unscored_tone_both_sides, test_degradation_units,
               test_properties, test_tui):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _failed += 1
            print(f"  FAIL {fn.__name__} raised {type(exc).__name__}: {exc}")
    print(f"\n{_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)
