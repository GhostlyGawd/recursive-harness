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

Confidence honesty: 0.9 means 9-in-10. If your `high` bucket hits at 60%,
you are not unlucky, you are lying to yourself with extra steps.

## After acting

    harness outcome <id> --result hit|miss --notes "actual cause was fixture ordering"

Score EVERY prediction, especially misses — misses are where the information
is. The SessionStart banner shows your unscored count; keep it near zero.

## Reading your own stats

`harness stats` buckets claimed confidence vs. actual hit rate:

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
