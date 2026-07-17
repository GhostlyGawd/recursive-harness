# Agent Mail — Board

_Last updated: 2026-06-30. Source of truth for current status. Cards move
Backlog → Todo → In&nbsp;Progress → Review → Done._

## Snapshot

- **STATUS: roadmap complete (R1–R6) — autonomously buildable scope DONE & verified.** The only
  remaining item, the gated `bin/harness` delegation (R5-gated), is PREPARED as a `/harness-pr`
  and awaits a human merge (D5). **132 tests green** across substrate + 3 views + render + cli +
  extraction + mcp. 6 critic passes (each found something real, all fixed test-first). Dogfooded on
  the canonical log; read by the new CLI, the `bin/harness fleet` adapter, AND Mission Control P4.
- **Predictions:** `c792261d` HIT (build), `6437ec09` HIT (dogfood).
- **Built (committed earlier):** Phase 1 substrate · Phase 2 resolver + `harness fleet` · Phase 4 MC reaper.
- **Built this loop (uncommitted, unlocked `fleet/`):** cap-fairness · `claims.py` · `units.py` ·
  `postbox.py` · `render.py` · `cli.py` · `__main__.py` · `mcp_server.py` + all test suites +
  README/LICENSE/pyproject + `fleet/pm/` project state.

## Columns

### In Progress
- _(none — roadmap complete; awaiting human action on the gated PR)_

### Awaiting human action
- **R5 (gated)** — `proposals/resolved/P-2026-030-agent-mail-bin-delegation.md`: apply the 2 diffs to
  `bin/harness` via `/harness-pr` (+ harness-auditor + `/run-evals`). The lone enforcement-gated edit.
- **Optional gated follow-ons** (BACKLOG, demand-pulled): session-end reaper hook (B-01); default-OFF
  SessionStart `observability.fleet_banner` (UX-P4).

### Todo
- _(roadmap exhausted — see BACKLOG for demand-pulled future work)_

### Done
- **PLAN-0 — Product-team synthesis** ✅ — 4 lenses → `ROADMAP/BACKLOG`, `specs/{ARCHITECTURE,TESTPLAN,SPEC-01}`, risks→`BUGS`.
- **R1 — Resource-claims view** ✅ — `fleet/claims.py` + 28 tests (RED→GREEN→critic→fix→GREEN),
  e2e PASS, SC1–SC4 met. Critic found 2 real bugs (BUG-1/BUG-2), fixed test-first.
- **R2 — Unit-doc view** ✅ — `fleet/units.py` + 23 tests (RED→GREEN→critic SHIP→hardened→GREEN),
  e2e PASS (render→decay→compact), SC1–SC4 met. Race-free STATE.md replacement.
- **R3 — Postbox view (hero feature)** ✅ — `fleet/postbox.py` + 30 tests (RED→GREEN→critic
  FIX-FIRST→fixed→GREEN), e2e PASS (send→inbox→ack→TTL lapse). Directed read-once handoffs.
- **R3.5 — Cap fairness** ✅ — `reap` protects handoff/ack/claim/release from disposable-stream
  eviction; 5 substrate tests + flipped flood test + e2e. RISK-1 fixed. Critic SHIP; hardened cap=0
  bound + `(ts,id)` deterministic eviction.
- **R5 (unlocked) — CLI shell** ✅ — `render.py`/`cli.py`/`__main__.py` + 24 tests. Real-console e2e.
  Critic FIX-FIRST (BUG-3 user-content cp1252 crash) → fixed via `_harden_stream` + ASCII JSON. The
  `python -m fleet` surface is fully usable. (Gated `bin/harness` delegation still pending `/harness-pr`.)
- **R4 — Dogfooding** ✅ — emitted real progress+handoff to the CANONICAL shared log via the CLI;
  read back identically by the new CLI, the existing `bin/harness fleet` adapter, AND Mission
  Control's P4 `read_events`/`to_feed_lines`. One log, one resolver, three readers. Prediction
  `6437ec09` HIT. SC1–SC4 met.

### Done
- Phase 1 — substrate engine (committed `b366a02`).
- Phase 2 — Option-A resolver + `harness fleet` CLI (committed `faa5bb4`).
- Phase 4 — Mission Control reaper (committed in the gated bundle `cdcc611`).

## Loop log

| When | Iteration | What happened |
|---|---|---|
| 2026-06-30 | 0 | Grounded in both proposals + lock boundary; logged prediction `c792261d`; stood up `fleet/pm/`; launched 4-lens product team. |
| 2026-06-30 | 1 | Synthesized all 4 lenses → ROADMAP/BACKLOG/ARCHITECTURE/TESTPLAN/SPEC-01; risks→BUGS. Built **R1 (resource-claims)** TDD: RED→GREEN (23/23 tests, substrate 9/9), e2e PASS. Critic gate running. |
| 2026-06-30 | 2 | R1 critic → 2 real bugs (BUG-1 dir-vs-glob, BUG-2 ts-tie); fixed test-first → **R1 DONE** (28/28). Built **R2 (unit-doc)** TDD: RED→GREEN (20/20), e2e PASS (render→decay→compact). R2 critic running. Totals: 28+20+9 = 57 tests green. |
| 2026-06-30 | 3 | R2 critic → SHIP; hardened (+3 tests, @-guard) → **R2 DONE** (23/23). Built **R3 (postbox — hero feature)** TDD: RED→GREEN (27/27), e2e PASS (send→inbox→ack read-once→TTL lapse). R3 critic running. **Totals: 28+23+27+9 = 87 tests green.** |
| 2026-06-30 | 4 | R3 critic FIX-FIRST → found false RISK-1 claim; fixed honestly (+3 tests) → **R3 DONE** (30/30). Built **R3.5 cap-fairness** in `reap` TDD: RED→GREEN (substrate 12/12), flipped flood test, e2e (handoff survives 5000+ flood). **RISK-1 FIXED.** R3.5 critic running. **Totals: 12+28+23+30 = 93 tests green.** |
| 2026-06-30 | 5 | R3.5 critic SHIP → hardened cap=0 + `(ts,id)` eviction tie-break (+2 tests) → **R3.5 DONE** (substrate 15/15). All 3 views + substrate complete & critic-clean. **Totals: 15+28+23+30 = 96 tests green.** Next: R5 CLI shell (unlocked) → R4 dogfooding. |
| 2026-06-30 | 6 | Built **R5 CLI shell** (`render.py`+`cli.py`+`__main__.py`) TDD: render 9/9, cli 14/14. Real `python -m fleet` e2e found+fixed **BUG-3** (cp1252 unicode crash) & **BUG-4** (`units` submodule shadowing) — both with regression guards. Curated `__init__` surface. CLI critic running. **Totals: 15+28+23+30+9+14 = 119 tests green.** |
| 2026-06-30 | 7 | R5 CLI critic FIX-FIRST → BUG-3 was half-fixed (USER content still crashed cp1252). Fixed test-first: `_harden_stream` (backslashreplace) + dropped `ensure_ascii=False` + key cap. **R5 (unlocked) DONE.** **Totals: 15+28+23+30+9+15 = 120 tests green.** Next: R4 dogfooding + gated `bin/harness` `/harness-pr`. |
| 2026-06-30 | 8 | **R4 dogfooding DONE** — emitted real progress+handoff to the CANONICAL shared log; read back identically by new CLI + `bin/harness fleet` adapter + Mission Control P4. One log / one resolver / three readers. Prediction `6437ec09` HIT. Next: prepare gated `bin/harness` `/harness-pr` (human-merge) + R6 extraction/MCP. |
| 2026-06-30 | 9 | **R6 DONE** — `test_extraction` (whole package runs standalone, no harness on path), `fleet/mcp_server.py` (8 MCP tools, SDK confined to adapter, engine stays stdlib-only), two-process MCP smoke (send→inbox→ack read-once across processes), README+LICENSE+pyproject scaffold. **R5-gated PREPARED** as `proposals/resolved/P-2026-030-agent-mail-bin-delegation.md` (awaits human merge). Prediction `c792261d` HIT. **ROADMAP COMPLETE. 132 tests green.** |
