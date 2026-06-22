#!/usr/bin/env python3
"""Smoke tests for Mission Control P1. Two tiers, same runner style as cartograph/test_mission.py:
  [1] data firewall - pure logic on the fixture payload; runs WITHOUT textual installed.
  [2] textual pilot - mounts the app headless and asserts chrome / lanes / selection-follow.
      SKIPPED (not failed) if textual is absent, so tier [1] still gates in a no-dep environment.
Run:  python mission_control/test_smoke.py      # exits non-zero on any failure
"""
import asyncio
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # repo root on path -> `import mission_control` works

from mission_control import data
from mission_control.data import (
    STATE_ACTIVE, STATE_BLOCKED, STATE_PROPOSED,
    component_lanes, health_summary, inflight_summary, structure_summary,
)

FIXTURE = os.path.join(HERE, "fixtures", "sample_mission.json")
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


def test_data():
    print("[1] data firewall: lanes / state / health derive from the payload, never invented")
    payload = data.load_payload(FIXTURE)
    lanes = component_lanes(payload, sort="pressure")
    check(len(lanes) == 5, f"5 work components -> 5 lanes (got {len(lanes)})")
    check(lanes[0].state == STATE_BLOCKED, "pressure sort floats the BLOCKED lane to the top")
    check(lanes[1].name == "BIN/HARNESS" and lanes[1].state == STATE_ACTIVE,
          "next lane = the highest-pressure ACTIVE component (bin/harness, 3 followups)")
    states = {l.state for l in lanes}
    check({STATE_BLOCKED, STATE_ACTIVE, STATE_PROPOSED} <= states,
          "active / blocked / proposed states all represented")
    h = health_summary(payload)
    check(abs((h["hit_rate"] or 0) - 0.8) < 1e-9, "health.hit_rate folded through (0.8)")
    check(h["eval_present"] == 7 and h["eval_total"] == 7, "eval_cases present/total folded")
    inf = inflight_summary(payload)
    check(inf["active_sessions"] == 2 and len(inf["lease_holders"]) == 1,
          "in_flight crumbs: 2 sessions + 1 trunk-lease holder")
    check(structure_summary(payload)["nodes"] == 112, "structure node_count folded")
    # honesty contract: an empty payload degrades to empty, it does NOT fabricate zero rows
    check(component_lanes({}) == [], "empty payload -> no lanes (degrade, do not fabricate)")
    check(health_summary({})["hit_rate"] is None, "absent health -> None, not a fake 0")


async def _pilot():
    from textual.widgets import Static
    from mission_control.app import MissionControl
    payload = data.load_payload(FIXTURE)
    app = MissionControl(lambda: payload, name_label="MISSION CONTROL", channel="01")
    async with app.run_test() as pilot:
        await pilot.pause()
        chrome = str(app.query_one("#chrome", Static).render())
        rows = list(app.query(".lane"))
        detail0 = str(app.query_one("#detail-body", Static).render())
        check("MISSION CONTROL" in chrome, "chrome bar shows the identity")
        check("80%" in chrome, "chrome bar shows live calibration (CAL 80%)")
        check("234" in chrome, "chrome bar shows live structure (EDGES 234)")
        check(len(rows) == 5, f"5 lanes mounted (got {len(rows)})")
        check(app.selected == 0, "selection starts at lane 0")
        check(app.lanes[0].name in detail0, "detail bay follows lane 0 on mount")
        await pilot.press("down")
        await pilot.pause()
        detail1 = str(app.query_one("#detail-body", Static).render())
        check(app.selected == 1, "down moves selection to lane 1")
        check(app.lanes[1].name in detail1, "detail bay followed selection to lane 1")
        await pilot.press("s")  # toggle sort -> full reload; must not crash, lanes re-mount
        await pilot.pause()
        check(len(list(app.query(".lane"))) == 5, "sort toggle re-mounts lanes (still 5)")


def test_tui():
    print("[2] textual pilot: app mounts headless, selection-follow works")
    try:
        import textual  # noqa: F401
    except ImportError:
        print("  skip (textual not installed) - pip install textual to run the TUI tier")
        return
    asyncio.run(_pilot())


if __name__ == "__main__":
    test_data()
    test_tui()
    print(f"\n{_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)
