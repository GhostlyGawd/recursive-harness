---
name: specialization
description: Use immediately when no installed skill covers a reusable domain, or when feedback, a mistake, or a better process shows that an existing skill is incomplete or wrong. Record the first observation, create or amend a private candidate, and dogfood it now. Follow provenance to the canonical skill instead of forking it. Recurrence strengthens evidence but never delays a proven correction.
---

# Specialization for Codex

Turn the first useful observation into a tested local candidate. The lifecycle
hook supplies the absolute CLI path plus Codex session and turn IDs. Use that path;
do not assume the current repository contains Recursive Harness.

Read `references/evolution-loop.md` before validating a candidate.

## Classify once

- `gap`: no available skill covers a reusable capability.
- `correction`: an existing skill produced or encouraged a wrong result.
- `improvement`: an existing skill worked, but feedback exposed a better process.

Project-only facts belong in project instructions. Code defects belong in the
project's defect loop. Wrong or missing reusable guidance belongs here.

## Record the first observation

Recall related evidence first:

```text
python "<cli-from-hook>" match --domain "domain"
```

Then record. Pass the `--provider codex`, `--session`, and `--turn` values supplied
by the hook:

```text
python "<cli-from-hook>" add --learning-kind gap \
  --domain "domain" --shape "specific missing reasoning" \
  --provider codex --session "<session>" --turn "<turn>"
```

For an existing skill, follow the provenance in its `SKILL.md` and add
`--target-skill`, `--target-provenance`, and `--source-skill` pointing to the
canonical source. Never edit the installed plugin cache as the owner.

`add` writes compact evidence to a provider-neutral private ledger and creates or
updates the candidate immediately. It never needs prior-chat access and must not
store transcripts or full prompts.

## Author and dogfood now

Open the printed candidate. Replace its draft marker with the smallest procedure
that addresses the evidence. Replay the triggering case with the candidate loaded
explicitly, compare before and after, and record the honest result:

```text
python "<cli-from-hook>" candidate dogfood <nid> \
  --case "triggering case" --before "observed baseline" \
  --after "candidate result" --outcome worked \
  --generalizes yes --verification "named check or fixture passed" \
  --provider codex --session "<session>"
```

Record `partial` and `failed` attempts too, then revise the same candidate. A new
gap needs a worked replay that generalizes. Corrections and improvements need a
worked replay with concrete verification. Remove the draft marker only after the
candidate is authored, then run:

```text
python "<cli-from-hook>" candidate validate <nid>
```

## Promotion boundary

Validation makes a first-observation candidate promotion-ready when proof is
strong. Recurrence only surfaces repeatedly unvalidated work; count is not proof.

Keep candidates local until the user approves a canonical change. After approval,
strengthen the provenance owner, add the triggering regression case, regenerate
provider packages, and use the owner's guarded review workflow. Mark it promoted
only after the canonical change is accepted.

provenance: 2026-07-18, first Codex adapter for Recursive Harness Specialization;
owner required immediate creation and dogfood for both missing capabilities and
provenance-owned skill improvements.
