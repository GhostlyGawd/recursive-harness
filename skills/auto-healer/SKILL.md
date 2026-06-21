---
name: auto-healer
description: Use the moment you fix a bug, see a failure recur, or catch yourself about to apply a fix that looks like a bandaid for one patched before. Logs each bug plus every attempted fix to a per-repo ledger (skills/auto-healer/heal.py), so a root defect resurfacing 'in a different shape' stays visible across sessions instead of re-patched blind. Pull the web via /heal — never pushed at you. Pairs with stuck-detection (the in-session ladder); this is the cross-session memory. Skip it and the next session re-pays the same failed attempts.
---

# Auto-Healer

Siloed bandaids recur because each fix is blind to the last. This is the
cross-session ledger that makes the web visible. Five concepts, each named once:
a **bug** is a root defect; an **attempt** is one tried fix, scored
worked/failed/partial; a **tag** is a `facet:value` label; a **link** is a
relation between two bugs; **review** is the pull that surfaces the web.

## When to log

- You just diagnosed or fixed a bug — log the **bug**, then the **attempt**.
- A failure you recognize recurs — `bug status <id> recurred` (do NOT mint a new
  bug; recurrence count is the signal).
- You are about to apply the SECOND workaround of one underlying flaw — that is
  the bandaid trap (stuck-detection strike 2). Log both sites as bugs, **link**
  them, and fix at the source instead of minting a third patch.

## How to log

Run from the working repo's cwd — heal.py keys the ledger by that repo:

```
python3 skills/auto-healer/heal.py bug add --summary "..." --tags area:hook,class:race [--links <id>]
python3 skills/auto-healer/heal.py attempt add <bug-id> --hypothesis "..." --fix "..." --outcome failed
python3 skills/auto-healer/heal.py attempt outcome <attempt-id> worked --notes "..."
python3 skills/auto-healer/heal.py bug status <id> healed|recurred|wontfix
python3 skills/auto-healer/heal.py bug tag <id> --add file:extract.py --remove class:race
python3 skills/auto-healer/heal.py bug link <id> <other-id>
```

(From another repo, invoke heal.py by its absolute path under the harness; it
still keys by your current cwd's repo.)

## Tagging discipline

Tags are `facet:value`. REUSE facet names — `area:`, `class:`, `symptom:`,
`file:`, `root:` — so clusters actually coalesce. Drifting facet names splits the
web (same rule as harness-authoring "one name per concept"). The relational value
lives in shared facets + links, not free-text summaries.

## The /heal review (pull only)

`heal.py review` (current repo) or `review --all-repos` (survey every tracked
repo) surfaces, in priority order: **ESCALATE TO SOURCE** (recurring + a failed
fix), **STUCK** (>=2 failed attempts, still live — bandaid risk), **RECURRING**
(came back), **TAG CLUSTERS** (>=2 live bugs share a facet), and **LINKED
CLUSTERS**. ESCALATE is the autophagic handoff: route it via /retro — mechanical
cause -> propose a hook; knowledge gap -> skill/reference; design flaw -> ADR
(grep memory/decisions/ first; a prior ADR may already have rejected this fix
class — see stuck-detection).

## Boundary vs stuck-detection

stuck-detection is the IN-session ladder (stop / switch strategy / escalate on a
repeated failure). auto-healer is the CROSS-session record: when stuck-detection
fires, log the bug here so the next session inherits the falsified hypotheses
instead of re-deriving them.

## Storage

`state/heal/<repo-key>/{bugs,attempts}.jsonl` under the harness root —
machine-local, gitignored, keyed per working repo. Monthly rollup into memory/ is
a deferred follow-up; v1 surfaces on review, not via gc.

<!-- provenance: 2026-06-21, session 04fb5c5c — user pitched "Auto-Healer": a per-repo bug+attempt ledger to stop siloed bandaids recurring "in a different shape". Scope fixed by AskUserQuestion to harness-owned skill / current-repo ledger / lean v1 (skill + /heal + heal.py helper, no locked-layer edit). Built in an isolation worktree because three guards blocked the contended main checkout. -->
