---
id: P-2026-017
title: Proposal: UTF-8-safe stdout/stderr on ALL locked Python entrypoints (cp1252 crash/mojibake)
status: approved
implementation: landed
created: 2026-06-23
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #135"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #135 |
<!-- proposal-history:end -->

## Historical record

# Proposal: UTF-8-safe stdout/stderr on ALL locked Python entrypoints (cp1252 crash/mojibake)

- **Date:** 2026-06-23
- **Status:** PROPOSAL — the fix touches `lint/` + `hooks/` (enforcement-locked), so it
  lands via `/harness-pr` + `HUMAN_APPROVED` + harness-auditor + `/run-evals`, not a
  unilateral edit.
- **Origin:** 2026-06-23 `/retro-backlog` sweep, session `1deaaa07` (a `/gc` run, 2026-06-20)
  — `lint` output rendered an em dash as a replacement char (`not a trunk artifact � lint
  skipped`), and the retro's own mining script crashed with `UnicodeEncodeError: 'charmap'
  codec can't encode character '→'`.

## Problem

The UTF-8 stdout/stderr fix already exists in **`bin/harness`** (commit `6005cf2`) and
**`hooks/inject_kernel.py`** (commit `390be28`). The remaining locked Python entrypoints still print
non-ASCII glyphs (em dash `—`, arrows `→`, box-drawing) with **no** `sys.stdout.reconfigure`.
On a cp1252 console (the Windows default on this host):

- output **mojibakes** (the lint's own messages are unreadable), and
- a glyph outside cp1252 — an arrow in a path/message, or CJK/emoji in **echoed user data**
  (a correction note, a skill tag) — raises `UnicodeEncodeError` **mid-print**. For a guard
  hook printing its BLOCK message, a crash mid-print is an enforcement-reliability bug, not a
  cosmetic one: the block text may not be delivered as intended.

This is the same cp1252 class already documented in `harness-authoring`
(sessions `dc1c3470`, `04fb5c5c`) — this proposal APPLIES that existing rule to the
entrypoints that commit `6005cf2` did not reach. It adds **no** new hook (consistent with
the standing "do not grow net hook count" mandate); it only hardens existing ones.

## Verified scope (grepped the tree, 2026-06-23)

11 entrypoints carry non-ASCII content AND have no `reconfigure` / `PYTHONUTF8` /
`codecs.getwriter`:

- `lint/lint_harness.py`
- `hooks/guard_enforcement_layer.py`
- `hooks/guard_worktree_isolation.py`
- `hooks/guard_worktree_session.py`
- `hooks/log_correction.py`
- `hooks/log_skill_use.py`
- `hooks/materialize_worktree_repos.py`
- `hooks/post_merge_return_to_trunk.py`
- `hooks/session_start.py`
- `hooks/stop_cadence_gate.py`
- `hooks/stop_retro_gate.py`

(`bin/harness` was fixed by `6005cf2` and `inject_kernel.py` by `390be28`. `guard_git_worktree_safety.py`,
`guard_trunk_lease.py`, `harness_features.py`, `session_end.py` are pure-ASCII today — lower
priority, but applying the idiom uniformly future-proofs them against a non-ASCII string being
added later.)

## Fix

At the top of each entrypoint's `main()` / module entry, the idiom `6005cf2` and
`skills/auto-healer/heal.py` already use:

```python
import sys
for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
```

- `errors="replace"` degrades a stray glyph to a replacement char instead of crashing.
- The `try/except` is load-bearing: hooks must **fail OPEN** (`harness-authoring`) — the
  reconfigure itself must never be able to brick a session (e.g. a wrapped/replaced stream).

## Why it matters now

A guard hook that crashes on `UnicodeEncodeError` while emitting its BLOCK message is an
enforcement reliability defect; `lint` mojibake erodes trust in the lint's own output. Both
recurred in this very sweep (the mining script crashed on `→`; the lint mojibaked a `—`).

## Prime-directive compliance

- **D2 route:** proposal (analysis) now; the `lint/` + `hooks/` edits are a separate
  enforcement PR.
- **D5 enforcement:** no unilateral edit — `/harness-pr` + human approval + harness-auditor +
  `/run-evals` (ADR 0003) before merge. The applier MUST run `/run-evals` because the diff
  touches enforcement paths.

<!-- provenance: 2026-06-23 /retro-backlog sweep, session 1deaaa07 (/gc, 2026-06-20). Scope
VERIFIED by grepping hooks/ + lint/ for reconfigure/PYTHONUTF8/codecs.getwriter vs non-ASCII
content on 2026-06-23: 11 entrypoints print non-ASCII with no UTF-8 stdout. Extends the same
cp1252 fix already in bin/harness (6005cf2) + inject_kernel.py (390be28). Same class as harness-authoring's
"Running scripts on this Windows checkout" section (sessions dc1c3470, 04fb5c5c). Adds no new
hook — hardens existing ones. -->
