---
name: harness-pr-ops
description: Use while DRIVING a harness change onto trunk — opening/merging PRs, especially several at once (a roadmap or /retro batch), or the moment a guard unexpectedly BLOCKS a git/gh/bin-harness command mid-flow. Encodes the operating mechanics the enforcement guards + GitHub impose that aren't obvious until they bite: stacked-PR merge order, running locked-path commands cleanly, and what to expect at the human gate. Pairs with harness-pr (the PR template), windows-host-paths (token mechanics), worktree.
---

# Operating a harness change through the guards

The PR *content* rules live in `harness-pr` + `harness-authoring`. This is the
*mechanics* of getting the change to land without fighting the guards or GitHub —
the footguns that cost re-work the first time you hit them. Each rule has a receipt.

## Stacked PRs — retarget the child BEFORE deleting the base
When PR-B is stacked on PR-A's branch (B's base = A's branch), merging A with
`gh pr merge A --delete-branch` deletes the branch B targets. GitHub does NOT
reliably retarget B — it **auto-CLOSES** B with a dangling base, and a closed PR
whose base branch is gone **cannot be reopened or rebased** (`gh pr edit --base`
and `gh pr reopen` both fail). You must recreate it as a new PR.

Do instead, in order: merge A → **`gh pr edit B --base main`** (retarget while B is
still open) → then merge/delete. Or simplest: merge A **without** `--delete-branch`,
retarget B, merge B, then delete both branches. Prefer not to stack at all when the
PRs touch different files (branch each off `origin/main` independently).
> receipt: session edd67875, 2026-06-28 — merged #200 with `--delete-branch`; its
> stacked child #201 auto-closed un-reopenably and had to be re-created as #203.

## Run locked-path commands on their OWN Bash call
The enforcement-layer guard blocks a Bash command when a **working-tree-mutating /
file-write token** co-occurs with a locked absolute-root path substring (`…/bin/harness`,
`…/hooks/…`, …) — it then reads the locked path as a WRITE target even when you only
EXECUTE it read-only. The triggering tokens are `git checkout` / `git restore`, `rm` /
`mv` / `cp` / `tee` / `sed -i`, a `>` / `>>` redirect, `open(…,'w')` — **NOT** `git merge`
or `git commit` (those are allowed alongside a locked path; verified empirically). Safe
habit: run a locked-path command (`bin/harness predict/outcome/…`) as its OWN call, never
chained after a `git checkout`/`restore` or a file write.
> receipt: session edd67875 — `git checkout main && git fetch && git merge … && python
> …/bin/harness outcome …` was blocked ("'bin' is enforcement-layer"); the `git checkout`
> was the trigger (a bare `git merge … && python …/bin/harness …` is NOT blocked). Splitting
> `bin/harness` onto its own call ran clean.

## A locked-layer build that adds test files: wire ci.yml in the SAME approve cycle
When an enforcement-gated change ALSO adds tracked `test_*.py` (a new file or whole new package),
`test_ci_coverage.py` requires each to be wired into `.github/workflows/ci.yml` (or excused in
`INTENTIONALLY_UNWIRED`) — and `ci.yml` is itself locked (`.github/`). So the ci.yml wiring is a
SECOND locked edit. Discover it UP FRONT and batch it into the same `bin/harness approve` →
edit-all-locked-files → `--revoke` cycle as your primary locked edit, instead of finding it after
the first commit and paying a second approve/revoke round-trip. Run `python3 tests/test_ci_coverage.py`
locally as part of pre-push validation so the requirement surfaces before CI, not after.
> receipt: session 89bd318f, 2026-06-30 — an `bin/harness` delegation landed first; only then did
> `test_ci_coverage` reveal 7 new `fleet/test_*.py` needed wiring into the (locked) `ci.yml`,
> costing a second approve cycle. Excused `fleet/test_mcp.py` (needs the `mcp` SDK CI lacks).

## The human gate is the EXPECTED terminus of locked-layer work — don't forecast auto-land
A change touching the locked layer (`hooks/ lint/ evals/ bin/ .github/ autonomy.json
settings.json templates/`) does NOT auto-merge. Even auditor-APPROVED, the binding gate
is the human PR merge (harness-pr step 6); the agent must not self-merge. Likewise a
proposed enforcement gate may be redesigned NON-locked, and `/run-evals` may be
proportionately WAIVED for an additive read-only change. So when you predict such a task,
the calibrated expectation is "stops at the human gate / redesigned / eval-waived," NOT
"lands this session." Over-forecasting clean completion missed TWICE in one session
(predictions 9e2786ec, 5309dd57 — both `enforcement-hooks`/`harness-authoring`, the
session's lowest-hit categories).

## Already documented elsewhere — go there, don't re-derive
- **Guard-bypass tokens must LEAD the command** (`HARNESS_TRUNK_LEASE_OK=1` no-ops behind
  a `cd …` or any non-leading position; cwd already persists, so never prefix `cd`):
  skill `windows-host-paths` §A (Manifestation A).
- **A commit message / PR body that NAMES the enforcement marker** trips the prose-scan
  on inline `-m`/heredoc text — write it to a file and use `git commit -F FILE` /
  `gh pr create --body-file FILE`: skill `harness-authoring` §"Mentioning the enforcement
  marker in a commit/PR body".
- **Branch hygiene** (return to trunk + `--ff-only` refresh after a PR): `harness-pr` step 7.

## Merging under branch protection
`main` requires the `lint-and-test` check on the CURRENT head AND an up-to-date branch.
After any merge lands, sibling PRs go `BEHIND`; `gh pr merge` then fails "Required status
check … is expected." Per PR: `gh pr update-branch N` → `gh pr checks N --watch` →
`gh pr merge N`. Do NOT reach for `--admin` to skip this — the up-to-date re-run is the
gate working, and bypassing CI on the harness is the reward-hack the kernel forbids.

<!-- provenance: session edd67875, 2026-06-28 (/retro) — a 5-PR Atlas roadmap surfaced four
operating footguns with no single home: stacked-PR --delete-branch auto-close (#201), the
locked-path path-scan on a chained command, branch-protection up-to-date re-runs, and the
human-gate-terminus calibration miss (×2). The leading-token + marker-prose mechanics already
live in windows-host-paths §A + harness-authoring; this hub cross-references them so the
PR-flow gotchas are discoverable from ONE trigger instead of re-derived each session. -->
