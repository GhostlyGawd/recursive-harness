# Mission Control

A Phosphor-Console TUI for total harness state. **Three lenses on one model** — Roster (P1),
Map (P2), and the Console station with Proof counters + a read-only live-feed Terminal (P3–P4) —
rendering the read-only `cartograph/extract.py --mission` payload (P0) and the `fleet.eventlog`
feed in the Lathe "Phosphor Console" design language. P5 (the anti-`STATE.md` guard) is merged.

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
| `↑`/`k`, `↓`/`j` | move the selection (detail bay follows) |
| `tab` | cycle the lens: Roster → Map → Console (selection follows the component) |
| `w` / `h` | toggle the work / health layer (light/darken gauges — never hides rows) |
| `s` | toggle sort (pressure ⇄ name) |
| `r` | reload the payload (and re-read the live feed) |
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

Three lenses on **one model** (selection follows the component across all of them, via `tab`):

- **Roster** (P1) — the Signal lanes full-screen.
- **Map** (P2) — the same components grouped by their loop, gauged by the same work-pressure model
  (node state by stroke); the detail bay shows a node's loop + edge degree. One model, two faces.
- **Console** (P3) — the station: lanes + a **Proof** panel (calibration / evals / predictions /
  corrections as big counters, honestly dashed when absent) + a **Terminal** ticker (P4: the live
  `fleet.eventlog` feed, newest-first, **read-only**). Layer toggles (`w`/`h`) light/darken the
  work/health gauges without hiding rows.

The data join is P0's: best-effort, by file path; anything unscoped stays unscoped, nothing is
invented. An absent ledger degrades to empty (never a fabricated zero). The Terminal reads the
canonical `state/fleet/events.jsonl` (resolved to the MAIN checkout from a worktree); it never
writes — emit/act, the reaper, and the `bin/harness fleet` subcommand shipped separately via
`/harness-pr` (the Terminal lens itself stays a pure reader).

## Design language

Phosphor Console, ported from `lathe/design/tokens.css` into `phosphor.tcss`: warm near-black
surface ladder (never blue/pure black); ONE amber phosphor accent lit only on live telemetry;
green/red quarantined to gauges; depth via surface steps + hairlines, never drop-shadows.

## Test

```bash
python mission_control/test_smoke.py      # [1] data firewall (no textual) + [2] pilot (Roster)
python mission_control/test_graph.py      # P2 Map lens + selection-follow
python mission_control/test_console.py    # P3 Console: Proof counters + layer toggles
python mission_control/test_feed.py       # P4 Terminal live-feed (read-only, fleet.eventlog)
python mission_control/test_robustness.py # hardening: markup firewall + loader error contract
```

## Hardening

Render and load-path robustness, locked by `test_robustness.py`:

- **Markup firewall** — every dynamic, payload-derived string (followup prose, proposal/file paths,
  event `kind`/`actor`/`target`/`payload`, the DATA-OFFLINE error text) is escaped before it reaches
  rich's `Text.from_markup`. Otherwise an orphan `[/]` in a followup *crashes* the render and any
  tag-shaped fragment (`[x]`, `arr[i]`, `[#zzz]`) is silently *dropped* — breaking the faithful-fold
  contract. Escaping runs **after** truncate+pad, so column widths (set on the visible text) hold.
- **Loader error contract** — `load_payload` (the `--json` path) mirrors `load_mission`: any failure
  (missing file, malformed JSON) re-raises as `RuntimeError`, the one exception `app.load()` catches,
  so a bad `--json` path degrades to "DATA OFFLINE …" in the chrome bar instead of crashing the TUI.

## Roadmap

- [x] **P0** — read-only `extract.py --mission` data layer (shipped, PR #109)
- [x] **P1** — TUI skeleton: chrome bar + Signal lanes (Roster) + detail bay
- [x] **P2** — Graph (Map) lens + selection-follow across lenses
- [x] **P3** — full Console station + Proof counters + layer toggles
- [x] **P4** — live-feed (Terminal) lens, **read-only** over `fleet.eventlog` *(emit/act shipped separately)*
- [x] **P5** — anti-`STATE.md` PreToolUse guard — **merged** via `/harness-pr`
  (`hooks/forbid_scratchpad.py`, wired in `settings.json`; test `tests/test_forbid_scratchpad.py`, 25/25)

### Landed — the gated work (merged via `/harness-pr` under recorded human approval)

- **P4 emit/act-from-it** — `bin/harness fleet emit|feed|reap` + the session-end reaper
  (`hooks/session_end.py`) shipped (Agent Mail PR #121 + the gated bundle).
- **P5 guard** — `forbid_scratchpad.py` moved to `hooks/` + registered in `settings.json`.
- **`harness mission-control`** launch verb wired into `bin/harness`; `/standup` carries its
  "launch mission-control" line.

The P0–P5 build is complete.

## Department notes (provenance + learning)

- **Born:** design locked with the user in
  `proposals/2026-06-21-mission-control-tui.md`; P1 skeleton `62661e2`
  (2026-06-21), P2–P4 lenses `a2f4ca8` (2026-06-23), gated P4/P5 items via the
  bundle `cdcc611`, hardening `8247ee2` (#212, 2026-07-01).
- **Extending:** the read-only invariant is the contract — a lens that writes
  is a different product; anything gated (guards, wiring, bin/ verbs) goes via
  /harness-pr as the P4/P5 precedent shows. The five test files run in ci.yml;
  `textual` stays out of the enforcement path (tests import-firewall the data
  layer).
- **When it breaks:** render/loader failures belong in test_robustness.py's
  two contracts (markup firewall, RuntimeError degradation to DATA OFFLINE);
  bugs route to the heal ledger; eval `mission-control-p2p5` fences the gated
  bundle.

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 14
(criterion 1): appended department notes (provenance/learning) to the existing
README; revise-not-rewrite. -->

