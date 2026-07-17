---
id: P-2026-006
title: Proposal: the correction detector logs the harness's OWN self-re-invocations as user corrections
status: approved
implementation: landed
created: 2026-06-21
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #111"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #111 |
<!-- proposal-history:end -->

## Historical record

# Proposal: the correction detector logs the harness's OWN self-re-invocations as user corrections

- **Date:** 2026-06-21
- **Status:** RESOLVED 2026-06-21 → implemented via PR `proposal/2026-06-21-correction-log-autonomy`.
  Open question answered: **`isMeta` is NOT delivered to the `UserPromptSubmit` hook stdin** (Claude
  Code hooks docs, verified 2026-06-21 — schema is `session_id, transcript_path, cwd, permission_mode,
  hook_event_name, prompt` + optional `agent_id, agent_type, effort`), so **Option A is dead**.
  `permission_mode` is also unusable: the silo runs `defaultMode: bypassPermissions`
  (`templates/account-settings.json`), so the human and the engine share the same mode. Final fix
  (all content-SHAPE, Option B phrase-denylist stays rejected): **(i)** skip sub-agent prompts
  (`agent_id`/`agent_type`); **(ii)** Option C tighten the bare `stop` token; **(iii)** honor a
  SIGNAL only inside the prompt's opening window (`prompt[:280]`).
- **Origin:** session e89c7b2c, 2026-06-20/21. A long autonomous-engine babysitting run
  drove its own cadence with `ScheduleWakeup`. The correction detector logged the agent's
  three self-authored wakeup prompts as "user corrections," and the Stop retro-gate then
  blocked stop with *"Retro gate: 3 user corrections this session"* — when the user issued
  **zero** corrections all session. Independently confirmed by the retro-miner.

## Problem (with code receipts)

`hooks/log_correction.py` pattern-matches every `UserPromptSubmit` prompt and appends a
correction on a hit. It filters exactly one programmatic class today:

```
hooks/log_correction.py:42  # Background-agent results reach this ... as <task-notification>
hooks/log_correction.py:45  if prompt.lstrip().startswith("<task-notification"):
hooks/log_correction.py:46      return 0
```

It has **no concept of the harness re-invoking itself**. Two non-user prompt classes slip
through and get logged as corrections:

1. **Self-scheduled `ScheduleWakeup` re-invocations** — the agent pacing its own loop. These
   arrive at `UserPromptSubmit` as fresh "user" prompts.
2. **Autonomous-subprocess bootstrap prompts** — e.g. an engine spawning `claude -p`
   worker/critic/curriculum/planner calls, whose initial prompts also reach the hook.

The match is easy to trip because the SIGNALS regex treats a bare `stop` token as a
correction:

```
hooks/log_correction.py:26   r"\b(no[,.]|...|stop[,. ]|undo|revert that|...)\b"
```

so an instruction like *"if you **stop** mid-cycle, clean with git reset"* — text the agent
wrote to ITSELF in a wakeup prompt — counts as a correction.

The downstream gate counts those same entries by session and blocks stop at 3:

```
hooks/stop_retro_gate.py:43   if json.loads(line).get("session") == session:
hooks/stop_retro_gate.py:47   if count >= THRESHOLD:
hooks/stop_retro_gate.py:53   reason: "{count} user corrections this session ..."
```

### Evidence (this session)

`harness corrections list` for the wakeup session `525e9a3e` holds **four** entries (and
the count keeps growing — one more per wakeup while the babysitting loop runs), **all
self-authored wakeup prompts**, none a user correction:

```
"Babysitting selfforge engine (background batch bznil8weu = `python forge.py run ...`)..."
"Babysitting selfforge engine — NEW batch byt56j8xw ..."
"Babysitting selfforge engine — batch byt56j8xw ..."
"Babysitting selfforge engine — batch byt56j8xw ..."   # +1 each subsequent wakeup
```

Token that matched the regex (verified): `'stop '` in *"...if you stop mid-cycle clean with
git..."* and `'STOP '` in *"...RED-FLAG STOP (TaskStop ...)..."*. The genuine interactive
session logged **zero** corrections. (The growing count is itself the tell: a value that
increments once per self-paced tick, never from human input, is not a "user correction.")

## Impact

`corrections.jsonl` is, by the kernel's own words, *"the highest-value training signal the
harness receives."* Polluting it with the harness's own loop traffic (a) falsely fires the
3-correction nudge and the once-per-session Stop retro-gate, (b) forces empty/padded retros
(the gate's premise is false), and (c) corrupts any future analysis that trusts the ledger.
The pollution scales with how much an agent self-paces or runs subprocesses — exactly the
long autonomous runs the harness is increasingly used for.

## Constraints that shape the fix

- **`hooks/` is enforcement-locked.** Implementation = `HUMAN_APPROVED` + harness-auditor +
  `/run-evals` + human-merged PR. Not a unilateral edit — hence this proposal, not a diff.
- **User taste (user-model L14):** minimize net friction; fix the root cause; *no
  guard-per-papercut / bandaid hooks.* The fix MUST be a **tightening of the existing
  filter** (one more skip branch in a hook that already exists), never a new guard. It
  *removes* false enforcement actions, which is the direction the user wants.
- **"False positives are cheap" is the hook's stated design** (`log_correction.py:8`) — true
  when a human types occasionally, false under machine self-loops that reliably hit `count==3`
  and weaponize the cheap-FP assumption into a hard stop-block.

## The fix — options

### Option A — flag-skip on `isMeta` (preferred, IF the flag reaches the hook)

The wakeup re-invocation record carries `isMeta: true` (verified in the `525e9a3e`
transcript jsonl). If that field is present on the `UserPromptSubmit` hook's stdin payload,
the fix is one branch, general, and not content-coupled:

```python
# After the <task-notification> skip:
# Self-scheduled wakeups & harness self-re-invocations are not user corrections.
if data.get("isMeta"):
    return 0
```

**OPEN QUESTION (must verify before drafting):** `grep -r isMeta` over the harness finds
**no** existing use, so it is unconfirmed that `isMeta` is delivered to the hook stdin (vs.
only living in the transcript record). The merging human (or a one-line stdin-dump probe)
must confirm. If present → Option A is most of the fix. If absent → the correct general fix
is to make the harness *pass* `isMeta` to the hook, NOT to fall back to content matching.

**RELIABILITY CAVEAT (auditor finding):** `isMeta` does not tag 100% of self-loop prompts
even in the transcript — at least one "Babysitting" wakeup record carried `isMeta` *unset*
(None), not `true`. So Option A alone may miss a fraction of the self-loop class. This is
exactly why **C is kept as a complement, not an alternative** — together they cover the
common self-loop prompt (A) and the specific `stop`-token over-match that does the actual
damage (C). Ship A+C, not A alone.

### Option C — tighten the `stop` signal (complementary, content-safe)

Independent of A, the `stop[,. ]` alternative is the specific over-match here. Requiring
correction-context (`stop (doing|that|it)\b`) would stop matching instructional "if you stop
…" text while still catching real *"stop doing that."* Small, defensible, reduces FPs
generally — but narrower than A (does not address the planner/bootstrap class).

### Option B — content denylist regex — ❌ REJECTED

A regex like `^(# Goal hierarchy|You are the planner|Babysitting .* engine)` was considered
and rejected: it is brittle (matches only THIS session's prompt phrasings), needs editing
for every new self-loop shape, and is exactly the bandaid user-model L14 forbids.

## Recommendation

Ship **A** if `isMeta` reaches the hook (one-branch, root-cause, general). Add **C** as a
cheap complementary tightening. Do **not** ship B. All inside the existing
`log_correction.py` — a net reduction in spurious enforcement, consistent with L14.

## Implementation notes (for whoever takes it)

- Confirm `isMeta` on hook stdin first (decides A vs. "teach the harness to pass it").
- One-time cleanup: the three spurious `525e9a3e` entries already in
  `state/corrections.jsonl` should be pruned so they don't seed a future false gate.
- Regression test to add (ADR 0003 corpus): a synthetic `UserPromptSubmit` payload with
  `isMeta:true` (and one with self-loop instructional text containing "if you stop") must
  log **zero** corrections; a genuine "no, that's wrong" payload must still log one.
- The Stop-gate message says "user corrections" with full confidence; once the source is
  cleaned it stays accurate, so no `stop_retro_gate.py` change is required — fix the source,
  not the symptom.

<!-- provenance: session e89c7b2c, 2026-06-20/21 — a ScheduleWakeup-paced autonomous-engine
babysitting run had its 3 self-authored wakeup prompts logged as user corrections (regex hit
on the bare token "stop " inside "if you stop mid-cycle"), which tripped the Stop retro-gate
with "3 user corrections this session" despite ZERO real corrections. Retro-miner confirmed
independently (entries under session 525e9a3e; genuine session logged none). Code receipts
read live: log_correction.py:26,42,45-46; stop_retro_gate.py:43,47,53. Routed as a PROPOSAL
(not a hooks/ diff) because (a) hooks/ is enforcement-locked and no HUMAN_APPROVED grant was
given, and (b) the final form depends on the unverified isMeta-on-stdin question — a human
must resolve that before the enforcement PR. -->
