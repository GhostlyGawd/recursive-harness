# Evidence and dogfood contract

Use this reference when an observation could create a new expert or change an
existing one.

## Classification

| Kind | Evidence | Immediate candidate | Sufficient first-observation proof |
| --- | --- | --- | --- |
| `gap` | No available skill covers a reusable capability | Seed a new expert | Triggering replay works, a second materially different case is represented, and `generalizes=yes` |
| `correction` | Existing guidance is demonstrably wrong | Copy the provenance owner and amend it | The original failure is reproduced, the amendment fixes it, and a regression check passes |
| `improvement` | Existing guidance works but can be measurably better | Copy the provenance owner and amend it | Before/after comparison improves the named measure without breaking the prior case |

Do not promote an unverified assertion. Store it as evidence and keep the
candidate `drafting` until a replay can falsify it.

For `correction` and `improvement`, target skill, provenance, and readable source
are mandatory inputs, and the target must match the source frontmatter name. If
the owner cannot be located, stop and resolve provenance; never substitute a
generic sibling candidate.

If a generic gap is later traced to an existing owner, archive the generic draft
and rebase the candidate from that owner. If the domain is already bound to a
different owner, reject the target change and resolve the domain collision.
Likewise reject a targetless gap observation for a bound domain so it cannot erase
the known owner between two corrections.

## Dogfood sequence

1. Preserve the triggering input, expected behavior, and observed failure as a
   compact case—not a transcript.
2. Establish the baseline from the actual event or a deterministic replay.
3. Author the smallest candidate that addresses the observed shape.
4. Load that candidate explicitly and repeat the case.
5. For a new expert, exercise a second shape or explain concretely why the
   procedure generalizes.
6. Record `worked`, `partial`, or `failed`, including the verification receipt.
7. Revise the same candidate after failure; never hide a failed replay.

## Promotion interpretation

- `validated` means the candidate has enough proof to ask for canonical review.
- `recurrence` counts distinct `provider:session` pairs and increases urgency.
- Recurrence never repairs weak proof and never delays a proven correction.
- `promoted` means the canonical owner accepted the change and provider adapters
  were regenerated; a private candidate alone is not an installed expert.

provenance: 2026-07-18, owner correction to the original recurrence-gated
specialization design and request for provenance-led skill improvement dogfood.
