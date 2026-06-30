#!/usr/bin/env python3
"""Robustness/hardening regressions for Mission Control — same runner style as test_smoke.py.

Locks two fixes found while hardening the shipped P0-P5 build (both were latent crashes on data the
read-only payload legitimately carries):

  R1 MARKUP FIREWALL. Every dynamic, payload-derived string the TUI renders (followup prose,
     proposal paths, file paths, event kind/actor/target/payload, the DATA-OFFLINE error text) is
     escaped before it is interpolated into rich's `Text.from_markup`. Without this, an orphan `[/]`
     in a followup CRASHES the render (rich MarkupError) and any tag-shaped fragment (`[x]`,
     `arr[i]`, `[#zzz]`) is silently DROPPED — violating the faithful-fold honesty contract.
     Escaping happens AFTER truncate+pad, so column widths (set on the visible text) are unchanged.

  R2 LOADER ERROR CONTRACT. `load_payload` (the --json path) mirrors `load_mission`: any failure is
     re-raised as RuntimeError, the only exception `app.load()` catches. Without this a bad --json
     path crashes the TUI with an uncaught FileNotFoundError/JSONDecodeError instead of the chrome
     bar's "DATA OFFLINE …".

Two tiers (mirroring the suite): [1] data firewall runs WITHOUT textual; [2] markup + pilot tiers
SKIP (not fail) when textual is absent.
Run:  python mission_control/test_robustness.py      # exits non-zero on any failure
"""
import asyncio
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # repo root on path -> `import mission_control` works

from mission_control import data

FIXTURE = os.path.join(HERE, "fixtures", "sample_mission.json")
# Adversarial text the payload can legitimately carry: an orphan close (crashed rich), a code
# subscript, a markdown checkbox, an invalid colour tag, and a link tag (silently dropped pre-fix).
ADVERSARIAL = "fix arr[i]; close orphan [/] tag; mark [x] done; colour [#zzz]; [link=x]click"
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


# ── R2: loader error contract (no textual needed) ────────────────────────────────────────────
def test_loader_contract():
    print("[1] loader firewall (R2): --json failures raise RuntimeError, never crash app.load")
    p = data.load_payload(FIXTURE)
    check(isinstance(p, dict) and bool(p), "a valid --json payload still loads to a non-empty dict")

    def _raises_runtimeerror(path):
        try:
            data.load_payload(path)
            return None
        except Exception as exc:  # noqa: BLE001 - we explicitly check the TYPE below
            return exc

    miss = _raises_runtimeerror(os.path.join(HERE, "no-such-file.json"))
    check(isinstance(miss, RuntimeError),
          f"missing --json file -> RuntimeError (got {type(miss).__name__})")

    bad = os.path.join(tempfile.gettempdir(), "mc_robustness_bad_payload.json")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("{not: valid json,,,")
    try:
        malformed = _raises_runtimeerror(bad)
    finally:
        os.remove(bad)
    check(isinstance(malformed, RuntimeError),
          f"malformed --json -> RuntimeError, not JSONDecodeError (got {type(malformed).__name__})")


# ── R1: markup firewall (builders are pure; importing them needs textual via app.py) ─────────
def test_markup_escaping():
    print("[2] markup firewall (R1): bracketed payload text renders literally, never crash/mangle")
    try:
        import textual  # noqa: F401
    except ImportError:
        print("  skip (textual not installed) - pip install textual to run the markup tier")
        return
    from mission_control.app import (
        chrome_markup, detail_markup, lane_markup, node_detail_markup, terminal_markup,
    )
    from mission_control.data import GraphNode, Lane
    from mission_control.feed import FeedLine

    lane = Lane(
        nid="skill:x", name="WEIRD[x]", type="sk[i]ll", file="skills/a[b]/SKILL.md",
        followups=[{"id": "abc123", "text": ADVERSARIAL}],
        proposals=["proposals/foo[bar].md"],
    )
    d = detail_markup(lane).plain   # .plain would already have raised on the orphan [/] pre-fix
    for frag in ("arr[i]", "[/]", "[x]", "[#zzz]", "a[b]", "foo[bar]", "WEIRD[x]", "sk[i]ll"):
        check(frag in d, f"detail bay preserves {frag!r} literally (no crash, no drop)")

    fl = [FeedLine(ts=0.0, actor="se[ss]", kind="cla[i]m", target="bin[/]h", text="val=[1,2,3]")]
    t = terminal_markup(fl).plain
    for frag in ("cla[i]m", "bin[/]h", "val=[1,2,3]"):
        check(frag in t, f"terminal ticker preserves {frag!r} literally")

    # esc() runs AFTER truncate+pad, so a bracketed type/name must not shift the gauge..name columns.
    seg = lambda s: s.split("fu ")[0]  # noqa: E731
    plain = lane_markup(Lane(nid="s:n", name="NORMAL", type="skill", file="")).plain
    brack = lane_markup(Lane(nid="s:b", name="WEIRD[x]", type="sk[i]ll", file="")).plain
    check(len(seg(plain)) == len(seg(brack)), "lane columns stay aligned regardless of brackets")

    g = GraphNode(nid="s:g", name="G[1]", type="t[2]", loop="lp[3]", file="f[4]")
    nd = node_detail_markup(g).plain
    for frag in ("G[1]", "t[2]", "lp[3]", "f[4]"):
        check(frag in nd, f"node detail preserves {frag!r} literally")

    ch = chrome_markup(
        "MISSION CONTROL", "01",
        {"session_owner": "a[b]", "branch": "feat/[x]", "lease_holders": []},
        {"hit_rate": 0.8}, {"nodes": 1, "edges": 1},
    ).plain
    check("a[b]" in ch and "feat/[x]" in ch, "chrome bar preserves bracketed sess/branch literally")


async def _pilot_resilience():
    from textual.widgets import Static

    from mission_control.app import MissionControl

    # (a) a RAISING loader degrades to DATA OFFLINE (no crash) — and its bracketed error renders.
    def boom():
        raise RuntimeError("extract.py exploded: stderr had [brackets] and a [/] in it")

    app = MissionControl(boom, name_label="MISSION CONTROL", channel="01")
    async with app.run_test() as pilot:
        await pilot.pause()
        chrome = str(app.query_one("#chrome", Static).render())
        check("DATA OFFLINE" in chrome, "a raising loader degrades to DATA OFFLINE (TUI does not crash)")
        check("[brackets]" in chrome, "the bracketed error text renders literally in the chrome bar")

    # (b) a bracket-laden payload mounts and the detail bay shows the literal followup text.
    payload = {"work": {"by_component": {"skill:x": {
        "component": {"type": "skill", "file": "skills/x/SKILL.md"},
        "followups": [{"id": "f1", "text": "see [/] and arr[i] then [x]"}], "proposals": [],
    }}}}
    app2 = MissionControl(lambda: payload, name_label="MISSION CONTROL", channel="01")
    async with app2.run_test() as pilot:
        await pilot.pause()
        detail = str(app2.query_one("#detail-body", Static).render())
        check("[/]" in detail and "arr[i]" in detail and "[x]" in detail,
              "a bracketed followup mounts + renders literally in the detail bay")


def test_resilience_pilot():
    print("[2] resilience pilot (R1+R2): raising loader -> DATA OFFLINE; bracket payload mounts")
    try:
        import textual  # noqa: F401
    except ImportError:
        print("  skip (textual not installed)")
        return
    asyncio.run(_pilot_resilience())


if __name__ == "__main__":
    test_loader_contract()
    test_markup_escaping()
    test_resilience_pilot()
    print(f"\n{_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)
