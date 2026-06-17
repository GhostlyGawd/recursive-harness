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

## Same root cause, different site (the workaround trap)

The ladder above keys on a repeated *identical* failure. This variant fires on a
repeated *workaround* of one defect across N call sites. When you reach for the
SECOND per-consumer patch of the same underlying flaw in a SHARED primitive
(design-system component, util, base class, schema), that IS strike 2 — STOP.
Fix it at the source instead of parking another local patch. Per-consumer
workarounds compound: every current and future consumer re-pays the same cost,
and the real defect is now hidden behind N divergent band-aids.

Tell: "I'll just add a conditional/override/guard here too, like I did in X."
If the cause lives upstream of the call site, the fix belongs upstream. If you
cannot fix the source now, escalate the source defect — don't silently mint a
third patch.

> provenance: 2026-06-16 cross-Grove retro; a @swarm/ui closed-overlay full-bleed quirk was worked around 3 separate times (B2 Dialog, W3 Sheet, a site consumer; transcript 6d93d19f) before one source fix (810c8b69). The Phase-6 source fix self-correcting the build is the evidence the rule is right; the two prior recurrences are what it cost.

## Afterwards, always

Log the prediction miss (`harness outcome <id> --result miss --notes ...`),
and route the lesson: mechanical cause → propose a hook; knowledge gap →
skill or reference; misread the user → user-model entry. A derailment you
don't route WILL recur, and next time it costs the same.
