---
name: auto-healer
description: Use the moment you fix a bug, see a failure recur, or are about to re-fix code you've touched before. `heal.py fix` logs the bug + scored attempt in ONE call (the low-friction primary path); `heal.py match` recalls prior FALSIFIED hypotheses for a file/error before you re-fix, so you don't re-derive dead ends. A per-repo bug+attempt ledger keyed by cwd makes a root defect resurfacing 'in a different shape' visible across sessions. Pull the web via /heal — never pushed. Pairs with stuck-detection (the in-session ladder); this is the cross-session memory.
---

# Auto-Healer

Siloed bandaids recur because each fix is blind to the last. This is the
cross-session ledger that makes the web visible. Five concepts, each named once:
a **bug** is a root defect; an **attempt** is one tried fix, scored
worked/failed/partial; a **tag** is a `facet:value` label; a **link** is a
relation between two bugs; **review** is the pull that surfaces the web.

## Capture: one call (the primary path)

The moment you fix — or fail to fix — something, log it in ONE call:

```
python3 skills/auto-healer/heal.py fix --summary "..." \
  --tags area:hook,class:race --hypothesis "..." --fix "..." --outcome worked
```

`--outcome` is REQUIRED (worked|failed|partial). Log failed/partial too — those
are exactly what surface STUCK and ESCALATE; a ledger of only-worked fixes hides
its own payoff. Omitting `--bug` mints a new bug, but if it looks like a
recurrence of a LIVE bug, `fix` REFUSES to mint a duplicate and tells you to
re-run `--bug <id> --recurred` (recurrence is a counter bump on the existing bug —
the count is the signal — never a fresh bug). `--force-new` overrides when it is
genuinely distinct.

Finer control is still there: `bug add` → `attempt add <id>` →
`attempt outcome <aid>`; `bug status <id> recurred|healed|wontfix`; `bug tag`;
`bug link <id> <other>`.

## Recall: look before you re-fix

Before drafting a fix for anything you recognize — or any file/area you've touched
before — pull what's already known so you don't re-walk falsified hypotheses:

```
python3 skills/auto-healer/heal.py match --file path/to/x.py --error "..."
```

`match` is read-only; it prints the matching bugs with every FAILED hypothesis
(the negative space) and any worked fix. This is the recall half of
stuck-detection's "search the record before re-fixing" — same pull, the
cross-session source. Logging is discipline; so is looking up.

## Tagging discipline

Tags are `facet:value`. REUSE facet names — `area:`, `class:`, `symptom:`,
`file:`, `root:` — so clusters coalesce. Drifting facet names splits the web
(harness-authoring "one name per concept"). The relational value lives in shared
facets + links, not free-text summaries.

## The /heal review (pull only)

`heal.py review` (current repo) or `--all-repos` surfaces, **ESCALATE-first**:
**ESCALATE TO SOURCE** (recurring + a failed fix), **STUCK** (>=2 failed, still
live — bandaid risk), **RECURRING**, **TAG CLUSTERS** (>=2 live bugs share a
facet), **LINKED CLUSTERS**. `--json` emits the same predicates for machine
consumers (one definition, no drift); `--escalate-only` is the /retro feed. A
`NO EVAL GUARD` mark means a recurring/escalate bug has no regression eval yet —
fix it once, guard it forever (below).

## Closing the loop: escalate → /retro → immunity

ESCALATE is the autophagic handoff. Route it via /retro — mechanical cause →
propose a hook; knowledge gap → skill/reference; design flaw → ADR (grep
`memory/decisions/` first; a prior ADR may already have rejected this fix class —
see stuck-detection). Once routed, run
`heal.py escalate route <bug-id> --session <id>` so it stops re-escalating on
every /heal. It stays **healing-aware**: a routed bug RE-escalates if a new failed
attempt lands after the route, and only fully drops when `healed`/`wontfix` —
routing once can never make an unhealed root go dark.

When you `bug status <id> healed` (or `fix --outcome worked`), heal prints a
ready-to-paste **/capture-eval scaffold** (it never writes `evals/` itself — that
is write-locked). Land the eval via /capture-eval so the defect can't silently
regress: a bug that recurs AFTER being healed is the strongest signal an eval is
missing.

## Boundary vs stuck-detection

stuck-detection is the IN-session ladder (stop / switch strategy / escalate on a
repeated failure). auto-healer is the CROSS-session record: when stuck-detection
fires, log the bug here (`fix ... --outcome failed`) so the next session inherits
the falsified hypotheses instead of re-deriving them.

## Storage & rollup

`state/heal/<repo-key>/{bugs,attempts}.jsonl` under the harness root —
machine-local, gitignored, keyed per working repo. `heal.py rollup --label
<repo-basename> [--trim-days 90]` versions a STATS-ONLY digest into
`memory/heal/<label>/<YYYY-MM>.json` (mirrors `memory/calibration/`; lessons still
route via /retro, never raw prose) and decays resolved `healed` records older than
N days — never `wontfix`, which is the falsified-hypothesis memory this skill
exists to keep. /gc and /meta-retro run the rollup; `cartograph --audit` reads the
same stats as an advisory harness vital sign.

<!-- provenance: 2026-06-21, session 04fb5c5c — user pitched "Auto-Healer": a per-repo bug+attempt ledger to stop siloed bandaids recurring "in a different shape". Scope fixed by AskUserQuestion to harness-owned skill / current-repo ledger / lean v1 (skill + /heal + heal.py helper, no locked-layer edit). Built in an isolation worktree because three guards blocked the contended main checkout. -->
<!-- provenance: 2026-06-21, session 908de0ac — v2 synergy build (user: "make it synergize with the harness"). `fix` one-shot becomes the primary capture path (required outcome + recurrence guard — no default-worked); `match` adds JIT recall; review prints ESCALATE-first with --json/--escalate-only single-sourced predicates; `escalate route` makes the heal→/retro loop real + healing-aware; on-heal /capture-eval scaffold turns a healed bug into permanent immunity; `rollup` versions a stats-only trend into memory/. Every proposal adversarially vetted vs ADR 0001 (no auto-memory) + the write-lock by a harness-auditor workflow before build. -->
