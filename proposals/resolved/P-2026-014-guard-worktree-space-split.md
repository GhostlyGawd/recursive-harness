---
id: P-2026-014
title: Proposal: `guard_worktree_isolation.py` false-blocks a `$VAR`-expanded path when the repo dir contains a SPACE
status: approved
implementation: landed
created: 2026-06-22
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #192"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #192 |
<!-- proposal-history:end -->

## Historical record

# Proposal: `guard_worktree_isolation.py` false-blocks a `$VAR`-expanded path when the repo dir contains a SPACE

- **Date:** 2026-06-22
- **Status:** PROPOSAL — the fix touches `hooks/` (enforcement-locked), so it lands via
  `/harness-pr` + `HUMAN_APPROVED` + harness-auditor + `/run-evals`, not a unilateral edit.
  Captured live as follow-up `e5264d`.
- **Origin:** session `453daf00`, 2026-06-22 — a routine Bash command was BLOCKED as a
  phantom cross-worktree write during the "Agent Mail" build.

## Problem (reproduced)

`guard_worktree_isolation.py` blocks a Bash command when it believes a token targets a
`.claude/worktrees/<name>` other than the session's own. When a shell variable holds a value
whose path contains a **space** — this repo lives at `D:\GitHub Projects\recursive-harness` —
`_expand_simple_vars` truncates that value at the space, and the truncated `$VAR` then
expands into a phantom `.claude/worktrees/<name>` operand that the foreign-worktree matcher
flags.

## Verified root (read in source + reproduced)

- **VERIFIED at `guard_worktree_isolation.py:315`** — `_expand_simple_vars`'s assignment
  regex is `(?:^|[;&|()\s])([A-Za-z_]\w*)=([^\s;&|()]+)`. The value group `([^\s;&|()]+)`
  stops at the first **space**, so a space-containing value (`MAIN=D:/GitHub Projects/recursive-harness`)
  is captured **truncated** as `D:/GitHub`.
- The truncated value substitutes into later `$MAIN` / `$WT` uses. When the result forms a
  `.claude/worktrees/<name>` operand (e.g. a `$WT` built from the truncated `$MAIN`), step 4a's
  `_WT_GLOB_RE` matches it as a foreign worktree and the guard blocks — reporting a truncated
  target id (observed: `d:/github/.claude/worktrees/lateral-coordination`, missing the
  ` Projects/recursive-harness` segment that lived before the space). Reproduced by a
  fresh-context harness-auditor against the live hook.

**What this is NOT** (corrected from this doc's first draft, which over-claimed — see the
provenance note): the block did **not** come from a `rm "$MAIN/state/fleet/events.jsonl"`
token (that expands to `D:/GitHub/state/fleet/...` — no `worktrees` segment; verdict `None`).
And `_bash_tokens` (line 426, `re.split(r"[\s;|&()<>]+", command)`) is a **separate, latent**
whitespace-split gap — it would split a *literal* spaced path — but it is **not** the site
that produced the observed block. The reproduced cause is the `_expand_simple_vars`
first-space truncation alone.

## Impact + why it matters now

A `$VAR` holding this repo's (space-containing) path false-blocks the moment it expands into a
`.claude/worktrees/<name>` operand — common here, since scripts build worktree paths from a
`$MAIN`/`$ROOT` base. (Per the auditor's reproduction, a fully-LITERAL absolute own-worktree
or trunk path still resolves correctly — the trip is specific to the var-expansion
truncation.) Worked around this session with relative paths + the
`HARNESS_ALLOW_CROSS_WORKTREE=1` prefix, but a guard that fires on correct commands erodes
trust and trains hatch-reflex.

This is the **5th logged instance of the Guard A parse-gap class** (follow-ups `ad0a9c`,
`9550a9`, `1b1ddc`, `109f86`, `e5264d`). **user-model L14: reduce net enforcement weight —
fix the parser ROOT, do not add another guard or special-case.**

## Fix options (PR author verifies + picks)

1. **Fix `_expand_simple_vars` (the reproduced root):** capture a space-containing assignment
   value correctly — track quoted values, or extend the value capture to the rest of the
   token — so `$VAR` expands to the FULL path. Narrowest fix for the observed block; verify it
   does not reopen an evasion the blanking/scrubbing was hardened against.
2. **Separately close the `_bash_tokens` whitespace-split latent gap** (a *literal* spaced
   path) — distinct from #1; a complete fix likely needs both.
3. **Deeper:** a cwd-jailed / sandboxed Bash policy instead of the literal command-string
   scanner — the standing answer to this whole parse-gap class. The recurrence (5th) is the
   case for it.

## Prime-directive compliance

- **D2 route:** proposal (analysis) now; the `hooks/` fix is a separate enforcement PR.
- **D5 enforcement:** no unilateral hook edit — `/harness-pr` + human approval + auditor +
  `/run-evals`.

<!-- provenance: session 453daf00, 2026-06-22. Guard false-block reproduced live (Agent Mail
build) and by a harness-auditor; root VERIFIED at guard_worktree_isolation.py:315
(_expand_simple_vars value regex `([^\s;&|()]+)` stops at the first space, truncating a spaced
value). _bash_tokens:426 whitespace-split is a SEPARATE latent gap, not the reproduced cause.
5th Guard A parse-gap (follow-ups ad0a9c/9550a9/1b1ddc/109f86/e5264d); user-model L14 = fix the
parser, not add a guard. NOTE: this doc's FIRST draft over-claimed — it mis-attributed the
block to the `rm` token and labeled _bash_tokens a co-equal "confirmed" cause; a harness-auditor
caught it (the exact failure the companion harness-authoring edit warns against), and this
version states only the source-read + reproduced facts. -->
