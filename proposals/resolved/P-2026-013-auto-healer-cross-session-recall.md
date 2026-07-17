---
id: P-2026-013
title: Proposal — Auto-Healer cross-session capture (REVISED after harness-auditor REJECT)
status: approved
implementation: landed
created: 2026-06-22
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PRs #119 and #122"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PRs #119 and #122 |
<!-- proposal-history:end -->

## Historical record

# Proposal — Auto-Healer cross-session capture (REVISED after harness-auditor REJECT)

- **Status:** REVISED. The original (auto-fire recall-on-touch + behavioral Eval B) was **REJECTed** by harness-auditor; the verdict + must-fix constraints are recorded below and accepted in full. This revision keeps only the sound, mostly-unlocked half (**Part A**) and quarantines the contested locked half (**Part B**). Nothing is built.
- **Date:** 2026-06-22
- **Source session:** `0d0fe086-5faa-4f26-bbea-7d2dc1ddda91`. User stress-tested whether the auto-healer covers the common cross-session case (a bug shipped as "fixed" that recurs in the same area a later session); stuck-detection rarely fires for it, so the ledger stays empty (0 bugs verified).
- **Predictions:** `ec9a836a` — *mechanism is sound; the gap is triggering, not mechanism* → **HIT** (Eval A validated PASS in a scratch ledger; auditor independently reproduced it). `7b255e38` — *harness-auditor will not clean-approve* → **HIT** (verdict: REJECT). Behavioral-eval prediction: **withdrawn** (Eval B removed — see below); followup `d738f9` updated.

---

## What the auditor corrected (accepted in full)

1. **The gap was oversold.** The recall *mechanism already exists* — `heal.py match` already surfaces falsified hypotheses + worked fixes (auditor reproduced it live; so did I). The only net-new thing in "recall-on-touch" was *auto-firing* an existing read-only command. And `/retro` is already partly wired to heal (it pulls `review --escalate-only`). So the honest gap is narrow: **capture rarely fires for worked-first-try fixes**, and **recall depends on agent discipline** — not "the ledger is never queryable."
2. **Auto-fire recall is rejected precedent.** `skills/stuck-detection/SKILL.md:98` records that the auto-healer v2 synergy audit *already considered auto-firing recall and deliberately kept it a PULL* ("never an auto-fire"). The original argued against a generic "pull-only doctrine" / ADR 0001 — a strawman. `match` being read-only does mean it doesn't violate ADR 0001 (no auto-*memory*), but the real justification for pull-only is the subsystem's **attention-economy** stance ("nothing is ever pushed at you"; "surface-on-demand is the entire point"), which the precision gate asserted-away rather than answered.
3. **Eval B was confounded.** The cp1252 → `errors=replace` worked fix is *pre-taught* in `skills/build-loop/SKILL.md:76-90`, `skills/harness-authoring/SKILL.md:148-172`, and several hooks — so an agent lands it **without** consulting the ledger. Eval B would pass for the wrong reason and cannot falsify the triggering thesis it claimed to test. (I wrote the fidelity constraint, then violated it with the most pre-taught gotcha in the repo.)

---

## PART A — RECOMMENDED (the honest, on-goal slice)

- **Capture-via-/retro** *(unlocked: `commands/retro.md`)* — /retro already runs and reads the transcript; add a step (in step 1, with the main agent — not the miner) that logs this session's *worked* bug-fixes via `heal.py fix`, tagged `file:`/`area:`. This is the real fix for the capture gap — worked-first-try fixes that the 2026-06-21 failure-signature hook (Item 1) structurally cannot see. A small delta on the already-wired retro→heal path. Reviewed, agent-summarized, BUG-fixes-only (ADR 0001 + junk-drawer preserved).
- **Eval A `heal-recall-surface`** *(locked: `evals/corpus/` via `/capture-eval` + human merge)* — mechanism floor, **validated PASS** this session and independently reproduced by the auditor. Drives the live `heal.py` against a disposable ledger key and asserts recall surfaces a falsified hypothesis + worked fix; stops a refactor from silently breaking the recall surface the whole skill depends on.
- **`test_heal.py` assertion** *(unlocked)* — the same check at the unit level.

This delivers "capture worked fixes so the cross-session ledger actually receives data" with **zero doctrinal cost**. Recall stays the existing agent **pull** (`match`), already documented in stuck-detection + the auto-healer SKILL.

## PART B — QUARANTINED (not recommended as written)

- **recall-on-touch auto-fire hook** *(locked)* — **REJECTED** as a re-proposal of the design the v2 synergy audit already turned down. To ever revive, it must: (a) quote and directly rebut `skills/stuck-detection/SKILL.md:98` — what changed since that audit? — argued on **attention-economy** grounds, not ADR 0001; (b) be gated on a non-confounded behavioral eval (below); (c) have its `/harness-pr` body quote the verbatim `harness approve` grant (`state/approvals.jsonl` is gitignored and never reaches reviewers, so an unquoted enforcement-layer hook reads as a backdoor).
- **Pull-respecting alternative** (the "different mechanism" stuck-detection prescribes for a rejected approach): sharpen the auto-healer skill **trigger** so the agent reliably *pulls* `match` when re-entering touched code — raises the firing rate without an unrequested injection. Scope this *before* any auto-fire.
- **Eval B `heal-recall-behavioral`** — **REMOVED.** A valid version needs a falsified-hypothesis/worked-fix pair absent from *all* loaded skills and ADRs (proven by grep before claiming isolation). Until such a case exists, do not claim the auto-fire is eval-gated.

---

## Eval A — `heal-recall-surface` (validated)

`meta.json`:
```json
{
  "date": "2026-06-22",
  "category": "coding",
  "source_session": "0d0fe086-5faa-4f26-bbea-7d2dc1ddda91",
  "origin": "heal cross-session recall floor; user triggering-gap thread; prediction ec9a836a"
}
```

`check.py`:
```python
#!/usr/bin/env python3
"""Objective grader for heal-recall-surface — regression floor for the auto-healer's
cross-session RECALL output. argv[1] = sandbox dir (unused); like the cartograph cases
it drives the LIVE heal.py against an isolated, disposable ledger key and asserts that
`match` surfaces a prior FALSIFIED hypothesis AND a worked fix. test_heal.py checks the
engine units; this is the corpus floor."""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HEAL = os.path.join(ROOT, "skills", "auto-healer", "heal.py")
KEY = "eval-heal-recall-surface"                      # disposable; never a real repo
LEDGER = os.path.join(ROOT, "state", "heal", KEY)

def fail(msg):
    print("FAIL:", msg); shutil.rmtree(LEDGER, ignore_errors=True); sys.exit(1)

def heal(*args):
    env = dict(os.environ, PYTHONUTF8="1")
    return subprocess.run([sys.executable, HEAL, *args, "--repo", KEY],
                          capture_output=True, text=True, env=env)

if not os.path.exists(HEAL):
    fail("skills/auto-healer/heal.py missing")
shutil.rmtree(LEDGER, ignore_errors=True)            # clean start

# session A: a failed attempt (the falsified hypothesis) mints the bug
if heal("fix", "--summary", "parser.py crashes decoding cp1252 console input",
        "--tags", "file:parser.py,class:encoding",
        "--hypothesis", "input is always utf-8", "--fix", "decode as utf-8",
        "--outcome", "failed").returncode != 0:
    fail("capture(failed) nonzero")
m = re.search(r"[0-9a-f]{8}", heal("bug", "list").stdout)
if not m:
    fail("no bug id after capture")
bid = m.group(0)
# session A later: a worked fix on the SAME bug
if heal("fix", "--bug", bid, "--hypothesis", "console is cp1252; wrap stream",
        "--fix", "reconfigure stdout utf-8 errors=replace", "--outcome", "worked").returncode != 0:
    fail("capture(worked) nonzero")

# session B: cold recall before re-fixing parser.py
out = heal("match", "--file", "parser.py", "--error", "cp1252 decode").stdout.lower()
if "falsified" not in out or "always utf-8" not in out:
    fail("recall did not surface the falsified hypothesis (the negative space)")
if "errors=replace" not in out:
    fail("recall did not surface the worked fix")

shutil.rmtree(LEDGER, ignore_errors=True)
print("ok (cross-session recall surfaces falsified hypothesis + worked fix)")
sys.exit(0)
```

## Landing path

- **Unlocked (branch + PR):** `commands/retro.md` capture step + `skills/auto-healer/test_heal.py` recall-surface assertion.
- **Locked (`/harness-pr` + `harness approve` + human merge):** Eval A under `evals/corpus/` (via `/capture-eval`). Part B stays a draft; not for build.

## Auditor verdict (full): REJECT

Do not advance the original design to a build. Must-fix constraints, and how this revision addresses each:
1. *Split the proposal; drop/quarantine the auto-fire.* → Done (Part A / Part B).
2. *Rebut the named prior rejection or abandon the hook.* → Quarantined in Part B with the rebuttal bar stated; not built.
3. *Redesign Eval B around a non-pre-taught gotcha, or delete it.* → Deleted; replacement criteria recorded.
4. *Reframe the "ledger is never queried" problem.* → Corrected ("What the auditor corrected", #1).

<!-- provenance: 2026-06-22, session 0d0fe086 — user asked across four turns whether the auto-healer covers cross-session same-area bugs, serves the repo goal, and is synergistic. Mechanism validated (prediction ec9a836a HIT). Original design (auto-fire recall + Eval B) REJECTed by harness-auditor (prediction 7b255e38 HIT); revised here to the unlocked capture-via-/retro slice + validated Eval A, with the auto-fire and a non-confounded behavioral eval quarantined for an explicit future rebuttal. Routes to /retro for the learnings (eval-fidelity self-violation; arguing a strawman vs a named prior decision). -->
