---
name: specialization
description: Use the moment you work in a domain with no skill covering it - a framework, tool, protocol, or problem-class faced from scratch. `python3 skills/specialization/needs.py add` logs the gap as a *need* with the shape it took; recurrence across sessions promotes it. When a need recurs (or `needs.py promote-check` flags one), distill the whole evidence cluster into an *expert* skill via harness-authoring - so next session inherits the expertise instead of re-deriving. How the harness grows its own specialists; pairs with routing-learnings (where) + harness-authoring (how).
---

# Specialization - the expert-accretion loop

The harness should get more capable as it works, without being told to. This is
that mechanism: every domain you reason about from scratch is a missing expert.
You log the gap, it accretes evidence across sessions, and once it has proven it
recurs you distill the accumulated evidence into a skill - a permanent specialist
you call next time instead of re-deriving. Five concepts, each named once:

- a **need** is one capability gap: a domain with no skill covering it.
- **evidence** is one session-observation of a need - what *shape* the gap took there.
- **recurrence** is the evidence count for a domain. It is the promotion signal.
- **promotion** is distilling a need's whole evidence cluster into an expert.
- an **expert** is the resulting skill package, callable forever after.

Don't wait for permission and don't wait for /retro. Logging is continuous and
cheap; promotion is gated by demonstrated recurrence so experts are earned, not
sprawled.

## 1. Detect & log - every session, as you work

When you catch yourself reasoning about a domain from scratch - a new framework,
API, protocol, file format, algorithm class, ops surface - and no skill fired for
it, that is a **need**. Before logging, recall so you don't split one need in two:

```
python3 skills/specialization/needs.py match --domain "kafka consumer groups"
```

Then log this session's **evidence** - the *shape* the gap took THIS time (the
specific thing you had to work out), not a generic label:

```
python3 skills/specialization/needs.py add \
  --domain "kafka consumer groups" --category infra \
  --tags area:streaming,class:rebalance \
  --shape "had to derive why a consumer rejoin triggered a full partition reshuffle"
```

`--shape` is what makes promotion smart: the expert is distilled from the real
shapes the gap took, not a textbook. **Reuse facet names** in `--tags`
(`area:`, `class:`, `tool:`) so related needs cluster instead of fragmenting
(the same `one name per concept` discipline as harness-authoring / auto-healer).

The ledger is event-sourced JSONL at `state/skill_needs.jsonl`, resolved to the
canonical main checkout - so evidence from every worktree and session lands in
one place. `add` prints the running recurrence and flags when a need crosses the
threshold.

## 2. Recurrence & promotion - mostly automatic

A need with recurrence >= threshold (default 3, `nudges.skill_gap_recurrence`)
is **promotable**. You don't have to remember to check: the `stop_skill_gap_gate`
hook reads the same predicate and nudges you, once per session, when a domain has
recurred with no expert. To check by hand:

```
python3 skills/specialization/needs.py promote-check        # or --json
```

## 3. Promotion - distill the cluster into an expert

This is the payoff. Do NOT research the domain generically. Pull the actual
evidence cluster - every shape the gap took, across every session:

```
python3 skills/specialization/needs.py list --domain "kafka consumer groups" --verbose
```

Then:

1. **Mark it building:** `needs.py status <nid> building` (stops re-nudging).
2. **Research, shaped by the evidence.** Spawn subagents (Explore / general-purpose
   / deep-research) aimed at the *specific shapes* the cluster recorded plus the
   domain's load-bearing intricacies and failure modes. Verify load-bearing claims
   against authoritative sources - this is reference material future-you will trust
   blind (harness-authoring source-of-truth gate).
3. **Codify the expert** via the **harness-authoring** skill (description budget,
   `references/` for depth, falsifiability, provenance citing the contributing
   session ids). The skill's body is the callable procedure; deep reference goes in
   `skills/<expert>/references/`. Use **routing-learnings** if part of the cluster is
   really a hook/command/ADR, not a skill - don't force everything into a skill.
4. **Close the loop:** `needs.py promoted <nid> --skill <expert-name>` and update
   the registry (below). The need drops out of `promote-check` for good.

A need that proves not worth an expert: `needs.py status <nid> wontfix` (it stops
nudging but stays as falsified memory - we considered it and declined).

## 4. The registry - memory/skill-needs.md

`state/skill_needs.jsonl` is the hot, machine-local accretion. The versioned,
human-readable, **relational** view is `memory/skill-needs.md`: each tracked need
with its `facet:value` tags, `[[links]]` to related needs and to the expert that
resolved it, and status. Update it when you promote a need or when a need is worth
tracking durably. It is the harness's map of its own capability frontier.

## 5. Boundaries - reuse, don't duplicate

- **routing-learnings** decides *where* a learning goes; **harness-authoring** is
  *how* to write any artifact to standard. This skill orchestrates them for the
  specific detect->accrete->distill loop; it does not re-implement either.
- **auto-healer** is the sibling pattern for *bugs* (per-repo defect ledger,
  recurrence -> escalate). This is the same shape for *expertise* (per-domain gap
  ledger, recurrence -> expert). If a recurring need is really a recurring *defect*,
  it belongs in auto-healer, not here.
- **Anti-sprawl is the recurrence gate.** A first-touch domain is logged, never
  built. Experts are earned by proven repeat-need, so the skills/ tree grows
  specialists that actually get called, not a junk drawer. /meta-retro prunes any
  expert that never fires.

<!-- provenance: 2026-06-27, session 9f6014a0 - user defined the recursive-harness thesis ("it should recursively create and improve itself and extend its capabilities over time... creating experts as you go to call upon in the future") and corrected that this must be autonomous, not user-prompted. Scope set via AskUserQuestion (recurrence-gated promotion + continuous live logging + distill-from-evidence-cluster) under a blanket execute-and-land grant. Ships with needs.py (the ledger), memory/skill-needs.md (the registry), and the stop_skill_gap_gate hook (the autonomous nudge). Mirrors the auto-healer accretion->promotion pattern. -->
