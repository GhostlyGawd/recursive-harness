---
id: P-2026-016
title: P5 — anti-`STATE.md` PreToolUse guard (MERGED via the gated bundle)
status: approved
implementation: landed
created: 2026-06-23
updated: 2026-07-17
owner: GhostlyGawd
resolution: "PR #143"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #143 |
<!-- proposal-history:end -->

## Historical record

# P5 — anti-`STATE.md` PreToolUse guard (MERGED via the gated bundle)

- **Date:** 2026-06-23
- **Status:** MERGED — applied via `proposals/resolved/P-2026-015-mission-control-gated-bundle/` (one
  `/harness-pr`, under a recorded human grant). The guard now lives at `hooks/forbid_scratchpad.py`,
  is wired in `settings.json` (matcher `Write|Bash`), and its test at `tests/test_forbid_scratchpad.py`
  (25/25). This doc remains as the design record; the merge steps below are historical.
- **Part of:** the Mission Control build (`proposals/resolved/P-2026-010-mission-control-tui.md`, P5 — the
  Contrarian arm). Ships after P2–P4 (Map lens, Console station, live-feed lens) landed non-locked.

## What it is
`forbid_scratchpad.py` — a PreToolUse hook that BLOCKS creating a **new** ad-hoc cross-session
scratchpad (`STATE.md` / `HANDOFF*.md` / `SCRATCH(PAD)*.md`) inside the harness repo, routing the
author to a durable artifact instead (a `harness followup`, a proposal `Status:`, or the PR body).
This is the Contrarian half of the Mission Control synthesis: the instrument must never compete with
a stale hand-rolled scratchpad. It mirrors `guard_enforcement_layer.py` (narrow repo scope, exit-2 +
stderr block contract, `dirname(dirname(__file__))` root).

## Why (evidence)
3+ projects independently hand-rolled `cartograph/STATE.md`, `plugins/prospector/STATE.md`,
`state/HANDOFF-*.md` ("living scratchpad across sessions… not harness memory"). They fragment
in-flight state and go stale — the exact sprawl Mission Control exists to cure.

## Contract (proved by the staged tests — `test_forbid_scratchpad.py`, 19/19 green)
- **Blocks (positive):** a NEW `STATE.md`/`HANDOFF*`/`SCRATCH*` via Write OR a Bash file-writer
  (`>`, `>>`, `tee`, `touch`, `cp`, `mv`, `install`, `dd`) inside the repo.
- **Stays silent (negative — the symmetric twin):** editing an EXISTING scratchpad (grandfathered),
  a normal file (`README.md`, `*.py`, `state/*.jsonl`), a scratchpad-named file OUTSIDE the repo,
  an `Edit`/`MultiEdit` (cannot create), and a Bash READ (`cat STATE.md`).
- Fails open on malformed stdin; never bricks the session.

## How a human applies it (the merge steps)
1. `git mv proposals/resolved/P-2026-016-mission-control-p5-guard/forbid_scratchpad.py hooks/forbid_scratchpad.py`
   (requires the `HUMAN_APPROVED` marker, since `hooks/` is locked).
2. Add a PreToolUse entry to `settings.json` (locked), mirroring the enforcement guard:
   ```json
   {
     "matcher": "Write|Bash",
     "hooks": [
       { "type": "command", "command": "python3 ~/.claude/hooks/forbid_scratchpad.py" }
     ]
   }
   ```
3. Keep the test as a regression: `git mv … /test_forbid_scratchpad.py tests/` (or run it in CI).
4. Run `/run-evals` + harness-auditor (already run on this branch) before merge.

## Tests
```bash
python proposals/resolved/P-2026-016-mission-control-p5-guard/test_forbid_scratchpad.py   # 19/19
```
After step 1 the import path changes to `hooks/forbid_scratchpad.py`; update the test's `sys.path`
insert accordingly (the logic is unchanged).
