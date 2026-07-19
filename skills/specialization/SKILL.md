---
name: specialization
description: Use immediately when no installed skill covers a reusable domain, or when feedback, a mistake, or a better process reveals that an existing skill is incomplete or wrong. Record the first observation, create or amend a private candidate, and dogfood it on the triggering case now. Follow provenance to improve the canonical skill instead of forking it. Recurrence strengthens evidence but never delays a proven correction.
---

# Specialization

Turn the first useful observation into a tested candidate. Do not wait for a
second session to learn; only permanent canonical changes wait for proof and
review.

Read `references/evolution-loop.md` when classifying evidence or deciding whether
a dogfood replay is strong enough.

## 1. Recall and classify

Before minting a new domain, recall related evidence:

```sh
python3 skills/specialization/needs.py match --domain "kafka consumer groups"
```

Classify the observation exactly once:

- `gap`: no installed skill covers a reusable capability.
- `correction`: existing guidance produced or encouraged a wrong result.
- `improvement`: existing guidance worked, but feedback revealed a better process.

Project-only facts route to that project's instructions. A code defect routes to
`auto-healer`. A reusable procedure routes here even on its first occurrence.

## 2. Record and create immediately

For a new capability:

```sh
python3 skills/specialization/needs.py add \
  --learning-kind gap --domain "kafka consumer groups" \
  --category infra --tags area:streaming,class:rebalance \
  --shape "had to derive why a consumer rejoin caused a full rebalance"
```

For an existing skill, follow its provenance to the canonical source and seed an
amendment candidate from that source. Corrections and improvements require all
three provenance arguments and a readable source skill; `add` rejects a generic
sibling draft when any is missing or the target does not match source frontmatter:

```sh
python3 skills/specialization/needs.py add \
  --learning-kind correction --domain "codex hook output" \
  --target-skill hook-authoring \
  --target-provenance "GhostlyGawd/recursive-harness@<commit>" \
  --source-skill skills/hook-authoring/SKILL.md \
  --shape "the documented output shape failed against the current host schema"
```

`add` appends compact evidence to the provider-neutral private ledger and creates
or updates `candidates/<domain-key>/` immediately. Never store transcripts or full
prompts. Multiple observations in one provider session add shapes but count as one
recurrence. If a generic gap later resolves to an existing owner, `add` archives
the generic draft and rebases from that owner. It rejects a domain already bound
to a different target skill, including a targetless gap observation; continue
through the known owner or resolve the collision instead of clearing provenance.

## 3. Author and dogfood now

Open the candidate path printed by `add`. Replace its draft marker with the
smallest evidence-shaped procedure. Use `harness-authoring` for duplication,
provenance, source-of-truth, and budget checks.

Replay the triggering case with the candidate explicitly in context. Compare the
actual before and after behavior, then record the result:

```sh
python3 skills/specialization/needs.py candidate dogfood <nid> \
  --case "consumer rebalance diagnosis" \
  --before "reasoned from scratch and missed the coordinator transition" \
  --after "candidate identified the transition and selected the verified fix" \
  --outcome worked --generalizes yes \
  --verification "replay fixture rebalance-v1 passed"
```

Log failed and partial replays too. Revise the same candidate; do not mint a
sibling. A new `gap` needs two materially distinct worked cases for the current
revision, including one marked `generalizes=yes`. A `correction` or `improvement`
needs one worked replay with concrete verification.

After authoring and successful dogfood, remove the draft marker and validate:

```sh
python3 skills/specialization/needs.py candidate validate <nid>
```

Validation makes the candidate promotion-ready after the first observation when
the proof is strong enough. Recurrence >= 3 only surfaces an unvalidated candidate
for urgent review; count alone is never proof.

## 4. Promote through the canonical owner

`promote-check` shows proof-ready and recurring-unvalidated candidates:

```sh
python3 skills/specialization/needs.py promote-check
```

Do not install, push, or open a cross-repository change without approval. After
approval:

1. Strengthen the provenance owner when one exists; do not create an overlapping
   skill.
2. Add the triggering case as a regression fixture.
3. Regenerate provider packages from the canonical source and run shared fixtures.
4. Land through the repository's guarded branch and review workflow.
5. Close the loop with `needs.py promoted <nid> --skill <name>`.

## Boundaries

- A missing binary is acquired and verified; record a specialization only when
  the reusable acquisition procedure itself was the knowledge gap.
- `routing-learnings` chooses the artifact; `harness-authoring` governs its form;
  this skill owns first-observation capture, candidate evolution, and dogfood.
- `auto-healer` records code defects and attempted fixes. When the root is wrong or
  missing reusable guidance, route that learning back here.
- Never edit an installed provider cache as canonical source. Follow provenance,
  update Recursive Harness, then regenerate and reinstall the adapter.

provenance: 2026-06-27, session 9f6014a0, original expert-accretion loop; revised
2026-07-18 after the owner required immediate first-observation creation plus
dogfooded improvements to existing skills instead of recurrence-gated learning.
