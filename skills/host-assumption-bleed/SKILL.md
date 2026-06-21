---
name: host-assumption-bleed
description: Use when designing or building a NEW project/system FOR the user — especially anything described as autonomous, self-governing, agentic, or self-improving. THIS harness's governance invariants (human-in-the-loop approval, a write-locked enforcement layer only a human PR may change, human-seeded work) are facts of the recursive-harness repo, NOT universal best practice. Importing them by reflex can negate a sub-project whose premise is autonomy. Before designing a sub-project's governance/safety, confirm whether a human gate is a real requirement or a cage you're copying.
---

# Host-Assumption Bleed

You operate inside a harness with strong, deliberate governance invariants: a human
approves every enforcement change, the enforcement layer is write-locked, learnings
flow only via human-reviewed PR, and prime directive #5 is "never touch the enforcement
layer unilaterally." These keep THIS repo safe. They are not laws of nature, and they
are not the right default for every system you build.

## The trap

When you build a NEW system for the user you reach for the governance model you live in
and bolt it on: locked layer, human-approval gate, human-seeded backlog. If the
sub-project's premise is AUTONOMY (self-governing / agentic / self-improving), that
default does not merely constrain it — it negates the thesis. A human-approval bottleneck
on an "autonomous" engine means it is not autonomous.

## The check — run it before designing a sub-project's governance

Ask, out loud, one question: **"Is a human-in-the-loop gate a REQUIREMENT of THIS
project, or am I copying my own cage?"** Answer from the project's stated premise, not
from your operating context. When the premise is autonomy, the answer is usually "cage" —
surface it and confirm with the user before you build, not after they reject it.

## Autonomy ≠ removing the guards. It = self-enforcing guards.

The reflex assumes the only safety is a human gate, so "autonomous" feels unsafe. It is
not, if you replace the human with checks the system cannot fake:

- self-generated work — it picks its own next tasks (a curriculum), not a human seed;
- self-approval by an INDEPENDENT fresh-context critic + a held-out eval/corpus;
- auto-revert when a GROUND-TRUTH metric regresses — the system corrects itself;
- a thin, un-rewritable **reality anchor**: only the few files that keep success honest
  (the real external metric source + an egress/deny floor) are locked — nothing else.
  Total creative autonomy; zero ability to fake, redefine, or buy success.

That set is what the user actually wanted; the human-gated design was the wrong reflex.

## Falsifiable trigger

If, on a build-for-the-user task, you are about to write "requires human approval" /
"locked, only a human may change" / "human-seeded" into a system the user called
autonomous — STOP. You are bleeding host assumptions. Re-derive the governance from the
project's premise.

provenance: session 3772bd2d, 2026-06-20 — built "selfforge" (an autonomous, self-improving
engine the user asked for) with a human-gated locked layer + human-seeded backlog,
reflexively imported from the recursive-harness it ran inside. The user rejected the entire
design ("If it doesn't pick its own work, then that's not fully recursive, and you totally
missed the point... approve itself autonomously... not even worth trying"). The pivot to
self-governance (self-written curriculum + independent-critic self-approval + auto-revert +
a thin reality-anchor floor) was the thesis from the start.
