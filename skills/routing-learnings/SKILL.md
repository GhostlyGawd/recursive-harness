---
name: routing-learnings
description: The anti-auto-memory router. Use this EVERY time you notice something worth remembering — a repeated mistake, a user correction, a procedure that worked, a preference, a project quirk — and especially whenever you feel the urge to "just note this down" in CLAUDE.md or memory. Also use during /retro to classify each mined learning. Routing prose into the wrong artifact is the primary failure mode of this harness; when in doubt, trigger this skill.
---

# Routing Learnings

A learning only counts if it lands in an artifact that changes future behavior.
Walk the tree top-down; first match wins.

## The decision tree

1. **Can it be enforced mechanically?** ("never X", "always Y before Z")
   → **hook**. Code that blocks beats prose that suggests, and costs zero context.
   Hooks are enforcement-layer: draft the script + settings entry, open a PR via
   /harness-pr, human merges. Never edit hooks/ directly.

2. **Is it a multi-step procedure you (Claude) will repeat across tasks?**
   → **skill**. Loaded only on trigger, so cost is ~its description.
   Follow skills/harness-authoring before writing it.

3. **Is it a workflow the USER initiates by name?** ("do a release", "run retro")
   → **command** in commands/. Keep under 80 lines.

4. **Is it a role that needs an isolated, fresh context?** (grading, auditing)
   → **agent** in agents/. If the role must not see your working context to do
   its job honestly (any evaluation of your own work), it MUST be an agent.

5. **Is it this user's taste, style, or recurring preference?**
   → one bullet in memory/user-model.md, formatted exactly:
   `- <claim> (evidence: N, last: YYYY-MM-DD, source: corrections|stated|inferred)`
   Lint rejects bullets without evidence counts. New entries start at evidence: 1;
   bump the count and date on each confirmation. Never write a horoscope.

6. **Is it a fact true of exactly one project?** (build quirks, domain glossary)
   → that project's CLAUDE.md, one line. If you later see it in a second
   project, promote it upstream (it was a #2 or #5 all along).

7. **None of the above** → discard. Most observations should die here.
   Hoarding is the failure mode this tree exists to prevent.

## Hard rules

- Every routed artifact gets a `provenance:` line: date, session, triggering
  event. Lint enforces this for post-v1 artifacts. Unsourced rules are rumors.
- One learning, one artifact. If it seems to need two, it is two learnings.
- A decision with alternatives that were rejected → also write a short ADR in
  memory/decisions/NNNN-slug.md so future-you doesn't relitigate it.
