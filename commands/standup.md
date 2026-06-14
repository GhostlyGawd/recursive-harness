---
description: Standup on the current project — what shipped, what's open, harness health — then the safe housekeeping sweep (prune merged branches, clear stale state), done not asked.
provenance: 2026-06-13, standup session (+ gotcha from session 61f58113); trigger: user asked for a standup three sessions running and each time approved the SAME manual cleanup (delete merged branches, clear a stale retro_gate marker), then asked to stop having to say yes — "they can just be done". Encodes the fetch-first bug that made `git --merged` lie.
---

Produce a standup for $ARGUMENTS (default: the current repo). Two parts: report,
then sweep. Run the sweep AUTOMATICALLY — do not ask per item; just report what
you swept. This command exists because the user approved the same sweep repeatedly.

## 1. Report (read-only — gather in parallel)
- Shipped: `gh pr list --state merged --limit 15` and `git log --oneline -15`.
- Open work: `~/.claude/bin/harness followup list`, then `git status -s`.
- Health: unscored predictions (`~/.claude/bin/harness stats` — unscored = debt),
  calibration (SessionStart banner), recent corrections
  (state/corrections.jsonl), cadence (sessions since /meta-retro, retro gate pending).
Lead with a 2-3 line TL;DR, then sections: Shipped / Open / Health / Suggested next.

## 2. Sweep (do it — every step here is safe and recoverable)
Order matters; step (a) is non-negotiable.
a. `git fetch --prune origin` FIRST. Without it `--merged` lies: on 2026-06-13
   local origin/main was stale, so a fully-merged PR branch (#12) showed as
   unmerged. Always judge merged-ness against a freshly-fetched origin/main.
b. If local main is BEHIND origin/main and the tree is clean: `git merge --ff-only`.
   If main has local-only commits, or the tree is dirty, skip and report — never
   force it.
c. Delete merged LOCAL branches with `git branch -d` (NEVER -D: -d refuses
   anything unmerged, which is the safety net). Never the current branch or main.
   Anything -d refuses, list under "kept (unmerged)" with its name — do not force.
d. Delete merged REMOTE branches. Re-derive the list from `git branch -r --merged
   origin/main` AFTER the step-(a) fetch (never a cached value); exclude
   `origin/main`, `origin/HEAD`, and any long-lived branch (master/develop/release/*).
   `git push origin --delete <names>` has NO unmerged-refusal of its own — unlike
   (c)'s `-d`, this list is the ONLY guard, so keep it tight. Skip anything with an
   open PR (`gh pr list --state open`). A branch merged by squash/rebase won't show
   in `--merged` (the safe side — it's kept); to prune those, confirm
   `gh pr view <branch> --json state` is MERGED, else leave it and report. Each
   delete recovers from its PR, so doing this unasked loses no history.
e. Clear stale `state/retro_gate_*` markers — any whose session id is NOT the
   current session (a prior session's gate is inert; the file is gitignored and
   regenerates). Keep the current session's marker. If the current id is unknown,
   keep the newest marker and clear the rest.

## 3. Close
- Fold the sweep result into the report: branches pruned (local/remote), markers
  cleared, and anything KEPT with the one-line reason. Silent truncation reads as
  "nothing to do" — say what you skipped and why.
- Out of scope here: the enforcement layer (hooks/ lint/ evals/ autonomy.json).
  Never delete a branch with unmerged commits, and never the branch you are on.
