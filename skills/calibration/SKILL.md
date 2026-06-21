---
name: calibration
description: Predict-then-score protocol. Use at the START of any non-trivial task (multi-file change, debugging session, design decision, anything you could be wrong about) to log a falsifiable prediction, and at the END to score it. Also use when the user asks "how confident are you", when choosing between approaches, or when /calibrate reports overconfidence in a category. This protocol IS the harness's verified self-awareness; skipping it makes your judgement unmeasurable.
---

# Calibration

Self-awareness you can't audit is vibes. This protocol replaces it with a ledger.

## Before acting

State, concretely, what success looks like — then log it:

    harness predict --task "fix flaky auth test" \
      --expect "root cause is async teardown; <=2 files touched; suite green in one run" \
      --confidence 0.7 --category debugging

A good `--expect` is one reality can contradict: file counts, pass/fail, the
named root cause, "user accepts without edits". "I will do a good job" is not
a prediction, it's a mood.

Beware the self-confirming `--expect`: a clause that asserts your OWN output is
correct ("surfaces the KNOWN X", "matches the map I built") makes a "hit" prove
only that the code reproduced your assumption — not that the assumption was right.
Tie at least one clause to something you did NOT author: user-confirmed intent,
external ground truth, an independent check. (2026-06-21: scored a "hit" on
"overlap detection surfaces the known brainstorm+huashu overlap" — the "known"
was my own hand-label, later admitted an artifact; the hit certified a mislabel.)

Confidence honesty: 0.9 means 9-in-10. If your `high` bucket hits at 60%,
you are not unlucky, you are lying to yourself with extra steps.

## After acting

    harness outcome <id> --result hit|miss --notes "actual cause was fixture ordering"

Score EVERY prediction, especially misses — misses are where the information
is. The SessionStart banner shows your unscored count; keep it near zero.

## A load-bearing prediction gates shipping

If a prediction underwrites the DELIVERABLE — its core behavioral claim, the
thing the user actually asked for — then while it is still `pending` or scored
`miss`, the work is NOT done and must NOT merge. Green gates (tests, lint, a
passing auditor, an eval run) verify the ARTIFACTS; they do not verify the CLAIM.
Resolve it by exercising the REAL path end-to-end — the actual tool / trigger /
environment, never a proxy — then score it before declaring done or merging.
Shipping on a self-flagged "unverified" load-bearing claim is how a green PR
delivers the opposite of the goal. (2026-06-20: merged a "rides into worktrees"
change while its own prediction 55b1735b said that exact behavior was unverified;
post-merge it scored a MISS and the whole goal had to be re-delivered.)

## Reading your own stats

`harness stats` reports two lenses on the same scored log — confidence buckets
(claimed vs. actual hit rate, auto-flagged on large drift) and a per-category
hit-rate breakdown (no flag; it always prints both):

- **Overconfident in a category** → before acting in that category, list two
  ways you could be wrong and check one. Note persistent drift in
  memory/calibration/notes.md with a date.
- **Underconfident** → stop hedging and over-asking; act, then verify.
- **Misses clustering on one category** → that's a missing skill or hook.
  Route it (skill: routing-learnings).

## Wrong-track detection in flight

While working, your prediction is the tripwire: the moment observed reality
diverges from `--expect` (extra files ballooning, new failure class, the
"quick fix" sprouting branches), stop and re-plan instead of pushing through.
That divergence-noticing reflex is the intuition this harness trains.
