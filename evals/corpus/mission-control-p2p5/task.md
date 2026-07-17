# Mission Control P2–P5 — regression eval

Mission Control is the harness's read-only control-room TUI
(`proposals/resolved/P-2026-010-mission-control-tui.md`). P2–P5 added the Map lens, the Console
station with Proof counters + layer toggles, a read-only live-feed Terminal, and the
anti-`STATE.md` PreToolUse guard. This case is the mechanical regression net that proves a
future harness change has not silently broken the load-bearing contracts those lenses bind to.

It is an **objective** case (`check.py`, no critic) and runs headless — no real terminal,
no `textual` widget pilot (the widget behaviour is covered by `mission_control/test_*.py`).
It asserts the four invariants that, if broken, mean Mission Control is regressed:

1. **P0 data contract (underlies Roster/Map/Console).** `cartograph/extract.py --mission
   --quiet` exits 0 and the payload still carries every key the TUI binds to in
   `mission_control/data.py`: `structure.{node_count,edge_count,nodes,edges}`,
   `work.{by_component,in_flight,followups_open}`, and
   `health.{predictions.{hit_rate,total,unscored},corrections_total,eval_cases.{present,total},
   structural_rot}`.

2. **P1 firewall.** `mission_control.data` and `mission_control.feed` import with `textual`
   forced unimportable — the data/feed layer must stay free of the TUI dependency (so the
   on-demand fold + CI path never pull `textual`).

3. **P4 live-feed lifecycle (read-only).** `fleet.eventlog.reap` drops a past-TTL event and
   keeps a live one; `read_feed` on an absent log returns `[]` without creating the log
   (read-only) and projects newest-first.

4. **P5 anti-scratchpad guard.** `forbid_scratchpad.py` (found in `hooks/` post-merge, else the
   staging copy) BLOCKS (exit 2) a new `STATE.md` via Write and via a Bash writer (`tee`), and
   STAYS SILENT (exit 0) on a normal file, an `Edit` (cannot create), and a Bash read.

A `FAIL:` line + non-zero exit means a regression; `ok` + exit 0 means the contracts hold.
The check resolves the repo root by walking up to the dir holding both `cartograph/extract.py`
and `mission_control/`, so it is valid whether run from `evals/corpus/` (post-merge) or from
the staging dir (pre-merge).
