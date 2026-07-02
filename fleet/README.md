# Agent Mail (`fleet`)

A lateral coordination channel for fleets of AI agents: an **append-only, typed, self-reaping
event log** plus projection views that let agents (across sessions, spawns, processes, machines)
pass *live, in-flight* state to one another directly — instead of each project hand-rolling a
`STATE.md` or relying on a blind lock.

> **Extraction scaffold (Phase 5).** This package began life native-first inside the
> `recursive-harness` repo and is built to lift out cleanly: the engine + views import **only the
> Python stdlib** and storage is **injected**. On extraction, this `README.md`, `LICENSE`, and
> `pyproject.toml` move to the new repo root (one level above the `fleet/` package).
> `fleet/pm/` (build-process state) is dropped on extraction.

## Why

The substrate is one append-only log of typed records
`{id, ts, actor, kind, target, payload, ttl_s, supersedes}`. Every view is a pure *fold* over it;
one reaper enforces the whole lifecycle (drop past-TTL, drop superseded, ring-buffer cap — with a
fairness floor so coordination-critical records aren't evicted by a disposable-chatter flood).

**Addressing contract (load-bearing):** `actor` is an **ephemeral per-op token**, never a durable
identity; recipients are **stable handles** (role / work-unit / topic, e.g. `@reviewer`). This
sidesteps identity churn — you address *a role you can re-embody*, not a session that vanishes.

## Views

| View | What it answers | Read entrypoint |
|---|---|---|
| **Live feed** | "what's happening right now" | `fleet.read_feed` |
| **Resource claims** | "who holds this file/glob — and what conflicts" | `fleet.read_claims`, `fleet.overlap_pairs` |
| **Unit doc** | "the in-flight state of this branch/PR/task" (a race-free `STATE.md`) | `fleet.read_unit` |
| **Postbox** | "directed, read-once handoffs addressed to me" | `fleet.read_inbox`, `fleet.send`, `fleet.ack` |

## Use it

**CLI**
```
python -m fleet --state-dir ./state emit claim --target src/auth.py --note "refactoring login"
python -m fleet --state-dir ./state emit progress --target migrate-auth --set pct=60
python -m fleet --state-dir ./state send reviewer --re fix/login --msg "ready for review"
python -m fleet --state-dir ./state feed
python -m fleet --state-dir ./state claims          # + overlap conflicts
python -m fleet --state-dir ./state inbox --as reviewer
python -m fleet --state-dir ./state ack 3f9a2b1c    # full or short id
```
Storage is injected: `--state-dir` > `$FLEET_STATE_DIR`. (Inside the harness, `bin/harness fleet`
resolves the one canonical state dir and forwards here.)

**Library**
```python
from fleet import send, read_inbox, ack, read_claims, read_unit
send("./state", "reviewer", re="fix/login", msg="ready")
for m in read_inbox("./state", handles={"reviewer"}):
    ...
    ack("./state", m)            # read-once consume
```

**MCP server** (for any MCP-capable agent)
```
pip install agent-mail[mcp]
FLEET_STATE_DIR=./state python -m fleet.mcp_server
```
Exposes `emit · feed · claims · unit · send · inbox · ack · release` as MCP tools. The MCP SDK is
imported only in the adapter, so the core stays stdlib-only.

## Design invariants

- **stdlib-only engine** (`fleet/eventlog.py` + view modules) — enforced by an import-contract test
  and a standalone-extraction test that runs the suite with no parent repo on `sys.path`.
- **typed/TTL'd/reaped** records, bounded payloads — no free-prose dumping ground.
- **pull, not push** — awareness surfaces are read on demand, never nagged.

## License

MIT — see `LICENSE`. (Phase-5 default; the originating proposal left MIT vs Apache-2.0 open.)

## Harness department notes (dropped on extraction, like `fleet/pm/`)

Everything below is recursive-harness context; the product sections above are
the extraction payload.

- **Provenance.** Designed in `proposals/2026-06-21-lateral-coordination-event-log.md`
  (a /brainstorm run), revised to PLAN v2 after a fresh-context auditor pass in
  `proposals/2026-06-22-agent-mail-product.md`. Engine landed `b366a02`
  (Phase 1, 2026-06-22); views + CLI + MCP server landed `4c94d58` (2026-06-30);
  `bin/harness fleet` became a full delegation to `fleet.cli` in `8b1b8c1`
  under `proposals/2026-06-30-agent-mail-bin-delegation.md` (explicit human
  grant recorded there).
- **Harness wiring (CONTRACT).** `bin/harness fleet <verb>` resolves the one
  canonical `state/` (main checkout, via git-common-dir) and forwards here;
  `hooks/session_end.py` runs the event-log reaper at session end (Mission
  Control P4 — fail-open, space reclamation only, every read is reap-aware);
  Mission Control's feed pane reads the same log read-only.
- **Operations.** Build-process state lives in `fleet/pm/` (BOARD, BACKLOG,
  ROADMAP, BUGS, TOOLING + specs/ incl. TESTPLAN — the SPEC-first discipline;
  spec numbers mirror roadmap R-numbers, 04 skipped because R4 was the
  dogfooding gate, not a feature spec). Extend by spec + test: all eight
  `fleet/test_*.py` are wired-or-excused — seven run in ci.yml; `test_mcp.py`
  is excused (needs the `mcp` SDK CI lacks — INTENTIONALLY_UNWIRED in
  tests/test_ci_coverage.py), run it locally when touching the adapter. The
  stdlib-only import contract and the
  standalone-extraction test are the two invariants a change must not break.
- **Failure & learning.** The failure mode the package kills is the hand-rolled
  cross-session STATE.md (see `hooks/forbid_scratchpad.py`, same Mission
  Control synthesis). Identity churn is the designed-around constraint
  (ephemeral `actor`, stable handles) — the same ADR 0007 wall the worktree
  guards hit. Bugs route to the heal ledger; design changes go through
  `fleet/pm/` specs, not ad-hoc edits; product-scale direction stays in
  proposals/ until decided.

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 13
(LOOP-CODIFY.md criterion 1): appended the harness-department section to the
existing product README (revise-not-rewrite; extraction note kept intact). -->

