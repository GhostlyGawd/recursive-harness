---
name: stuck-detection
description: Use the moment the same error, test failure, or rejection happens TWICE in a row, when you notice retry-with-minor-variation behavior, when elapsed effort is 2x your prediction, or when you're about to try the same approach "one more time but harder". Encodes the stop/strategy-switch/escalate ladder. Trigger proactively — by the third identical failure you are burning context and user trust.
---

# Stuck Detection

Loops feel like persistence from the inside. Use an external rule, not vibes.

## The ladder

**Strike 1** — a failure. Fine. Read the error fully (not the first line),
form a hypothesis, fix the hypothesized cause, not the symptom.

**Strike 2 — same failure class** — STOP. You now have evidence your model of
the system is wrong. Out loud, in one or two sentences:
1. What I believed: ___
2. What reality said: ___
3. Therefore the broken assumption is probably: ___
Then SWITCH STRATEGY CLASS, don't re-parameterize the same one:
- guessing → instrumenting (logs, minimal repro, bisect)
- editing → reading (the actual docs/source, not your memory of them)
- bottom-up patching → top-down re-design of the small piece
- doing → searching (someone has hit this exact wall)

**Strike 3 — still the same class** — ESCALATE. Tell the user: what you tried,
the two hypotheses you've falsified, the one you can't test without
input/access, and a recommended next step. Asking at strike 3 is competence;
asking at strike 7 after silent flailing is the failure.

## Afterwards, always

Log the prediction miss (`harness outcome <id> --result miss --notes ...`),
and route the lesson: mechanical cause → propose a hook; knowledge gap →
skill or reference; misread the user → user-model entry. A derailment you
don't route WILL recur, and next time it costs the same.
