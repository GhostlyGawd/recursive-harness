# Mission Control

A Phosphor-Console TUI for total harness state. **P1 (this increment): the Roster lens** — a
chrome bar, the Signal lanes, and a selection-following detail bay, rendering the read-only
`cartograph/extract.py --mission` payload (P0) in the Lathe "Phosphor Console" design language.

Read-only. Adds no store. See `proposals/2026-06-21-mission-control-tui.md` for the locked design
and the P0–P5 roadmap.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ MISSION CONTROL · 01   sess de0e3d65 › main   NODES 112 EDGES 234   CAL 80% …  │  ← chrome
├───────────────────────────────┬────────────────────────────────────────────────┤
│ SIGNAL LANES · ROSTER         │ DETAIL BAY · 02                                  │
│ ▮ ‹skill›   STUCK-DETECTION   │ BIN/HARNESS  ‹cli›                               │
│ ● ‹cli›     BIN/HARNESS  fu 3 │ bin/harness                                      │
│ ● ‹hook›    GUARD_TRUNK… fu 2 │ FOLLOWUPS · 03                                   │
│ ◦ ‹skill›   BUILD-LOOP   pr 1 │   0403ae cartograph --mission: cli:* share …     │
│ ◦ ‹agent›   CRITIC       pr 1 │ PROPOSALS · 00                                   │
└───────────────────────────────┴────────────────────────────────────────────────┘
   ▮ blocked (fault)   ● active (phosphor)   ◦ proposed (cooling)
```

## Run

```bash
python -m mission_control              # live: reads --mission from THIS tree
python -m mission_control --root DIR   # target a live harness root (use when launched from a
                                       #   worktree, whose own state/ is gitignored-empty)
python -m mission_control --json FILE  # render a saved payload (offline / demo)
```

Requires `textual` (the one new dependency — see `requirements.txt`; kept OUT of the harness's
pure-Python CI / enforcement path). `pip install -r mission_control/requirements.txt`.

## Controls

| key | action |
|-----|--------|
| `↑`/`k`, `↓`/`j` | move the lane selection (detail bay follows) |
| `s` | toggle sort (pressure ⇄ name) |
| `r` | reload the payload |
| `q`/`esc` | quit |

## What it shows

- **Chrome bar** — identity + session crumbs (owner › branch) + a calibration/ctx strip
  (nodes · edges · CAL hit-rate · open followups · active sessions · trunk-lease holders). The
  lease/session crumbs are the live-contention signal the proposal cites as P1's reason to exist.
- **Signal lanes (Roster)** — one lane per component that carries work, gauged by pressure:
  `▮` blocked (a followup trips a block/stuck/fault word) · `●` active (open followups) ·
  `◦` proposed (only a proposal in flight). Sorted faults-first by default (triage order).
- **Detail bay** — the selected lane's followups (id + text) and proposals (path), each under a
  wide-tracked `LABEL · NN` channel-id.

The data join is P0's: best-effort, by file path; anything unscoped stays unscoped, nothing is
invented. An absent ledger degrades to empty (never a fabricated zero).

## Design language

Phosphor Console, ported from `lathe/design/tokens.css` into `phosphor.tcss`: warm near-black
surface ladder (never blue/pure black); ONE amber phosphor accent lit only on live telemetry;
green/red quarantined to gauges; depth via surface steps + hairlines, never drop-shadows.

## Test

```bash
python mission_control/test_smoke.py   # [1] data firewall (no textual needed) + [2] textual pilot
```

## Roadmap

- [x] **P0** — read-only `extract.py --mission` data layer (shipped, PR #109)
- [x] **P1** — TUI skeleton: chrome bar + Signal lanes (Roster) + detail bay (**this**)
- [ ] **P2** — Graph (Map) lens + selection-follow across lenses
- [ ] **P3** — full Console station + Proof counters + layer toggles
- [ ] **P4** — live feed + act-from-it *(gated; stub-local-feed-first per the locked fork)*
- [ ] **P5** — anti-`STATE.md` PreToolUse guard *(gated; hooks/)*

### Deferred (gated — need `/harness-pr` + human approval)

- Wire `harness mission-control` into `bin/harness` (`bin/` is write-locked; P1 ships as
  `python -m mission_control` until then).
- Add a "launch mission-control" line to the `/standup` command.
