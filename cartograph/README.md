# cartograph/ — the harness's self-map department

## Identity

The engine that keeps a machine-truth map of the whole harness. A read-only
extractor (`extract.py`) builds a graph of every component — skills, hooks,
commands, agents, state ledgers — and the wiring between them (lifecycle
triggers, `settings.json` hooks, `/cmd` pointers), then renders it as
[`ATLAS.md`](./ATLAS.md) (durable structural map) and
[`ATLAS-PULSE.md`](./ATLAS-PULSE.md) (point-in-time strain: friction, load,
bug clusters). One-line role in the city: **the map room — every structural
question about "how is this wired?" is answered here, not by grepping.**

## Why it exists

The harness is wired by lifecycle triggers, `settings.json`, and command
pointers — connections an import-grep can never see. Before cartograph,
structural questions were answered by searching and guessing, and dead or
orphaned artifacts accumulated invisibly. Born in `0131936`
(`feat(cartograph): Living Harness Cartograph — extractor + map + eval
guard`); the Atlas renderer arrived in `e91aab2`, the health score (BET D)
in `3b761ab`. The design goal throughout: make structural rot *visible and
un-fakeable* rather than trusting the agent's self-report.

## Contract — how the rest of the city uses it

| Interface | What it does | Who calls it |
|---|---|---|
| `python3 extract.py --check` | **The gate.** Non-zero exit on un-baselined structural rot | CI (`ci.yml`), pre-merge, this loop's verify step |
| `python3 extract.py --audit` | Advisory dead-weight / drift feed | `/meta-retro` |
| `python3 extract.py --query <blast-radius\|dependents\|dependencies\|path\|orphans\|node\|governed-by\|traces> <target>` / `--context <node>` | Structural oracle: neighbors, paths, governance | skill `structural-qa` |
| `python3 extract.py --diff` | Structural review of a change | review flows |
| `python3 atlas.py` (via `/atlas`) | Re-render ATLAS.md + ATLAS-PULSE.md from machine-truth | `/atlas`, `/meta-retro` |
| `python3 health.py --trend` | One 0–100 structural vital sign over git history | `/meta-retro` (advisory only) |
| `baseline.json` | Fingerprints of grandfathered warnings the gate ignores | the gate |

Resolution note: `--query`/`--context` take a **node id, unique name, or
mapped artifact path** (a skill, hook, command…). Directories and
cartograph's own engine files are not nodes — for department-level questions,
read the relevant ATLAS.md section instead.

The load-bearing firewall: **the audit advises, the gate blocks, neither
acts.** The map can surface prune candidates but can never delete its own
nodes — a map that could prune itself to look clean is the exact corruption
mode the kernel forbids.

## Operations — extending it correctly

- Everything here is **read-only over the repo** by design; keep it that way.
- Changes go branch → PR like all trunk changes. `cartograph/` is not
  enforcement-locked, but it is test-covered: run every `test_*.py` in this
  directory (10 files, ~334 tests as of 2026-07), then `extract.py --check`,
  then the harness lint, before any PR.
- Deferred product bets live in [`ROADMAP.md`](./ROADMAP.md) (BET C:
  generalize the extractor beyond this harness; D/E follow-ons).
  [`STATE.md`](./STATE.md) is the cross-session build scratchpad — short,
  current, prunable; not harness memory (and it can go stale: trust git log
  over it). [`PLAN-oracle-reviewer.md`](./PLAN-oracle-reviewer.md) is the
  build plan for the oracle/reviewer bets.
- Map/structure questions are governed by skill `structural-qa`; authoring
  standards by skill `harness-authoring`.

## Failure & learning

- **Gate fails (`--check` non-zero):** new structural rot was introduced.
  Fix the wiring; only baseline a warning with human review and a reason.
- **Oracle can't resolve a target:** the target isn't a mapped node (common
  for directories/engine files) — fall back to ATLAS.md sections.
- **Map feels stale:** run `/atlas` to re-sync; PULSE is *meant* to drift
  and is committed deliberately at `/meta-retro` for a friction-over-time
  record.
- Bugs and falsified fix attempts are logged in the auto-healer ledger
  (skill `auto-healer`); recurring gaps route via skill `routing-learnings`.
