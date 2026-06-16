# ADR 0005: A ship-grade public venture owns its own fresh repo — products/<slug>/ is only for throwaway/internal ventures

date: 2026-06-16
status: accepted
provenance: 2026-06-16 cross-Grove retro — source: superset-replica-build/DECISIONS.md ADR-0001 (own fresh sibling repo) & ADR-0012 (making that repo public unblocked GitHub Actions billing), STATE.json (github.com/GhostlyGawd/grove); contradicts venture-build SKILL.md:35 + references/artifacts.md (the `products/<slug>/` scaffold). Folds own-fresh-repo x3.

## Decision
A venture intended to ship PUBLICLY gets its OWN fresh git repository — a sibling
of the harness, not a subdir of it. `products/<slug>/` inside the harness is
reserved for THROWAWAY or INTERNAL ventures (prototypes, demos, ventures that
will never have a public history, license, or release).

The trigger to branch on is **ship-grade-vs-internal**, decided at intake:
- Will it have a public repo, its own license, tagged releases, or its own CI
  billing? → own fresh repo.
- Is it a scratch/internal artifact that lives and dies inside the brain? →
  `products/<slug>/`.

## Why (the rejected alternative, and the receipts)
The rejected alternative is the current venture-build default: scaffold the
venture as a worktree/subdir of the harness (`products/<slug>/`). That is the
right call for internal work, but for a ship-grade venture a subdir of the
mono-repo brain CANNOT provide:
- an independent git history (the venture's commits tangle with brain commits),
- its own LICENSE and release tags,
- a public repository at its own URL,
- independent CI billing.

Binding a product's public history to the harness also **forks the brain**
(kernel directive 6) in the opposite direction — it drags ship-grade product
churn through the one trunk meant for learnings.

Grove proved this concretely, N=1 but unambiguous:
- **ADR-0001** chose an own fresh sibling repo over a harness subdir.
- **ADR-0012** showed that making that repo PUBLIC was the specific step that
  unblocked GitHub Actions billing — a capability a private subdir of the brain
  could not have surfaced.

Same root cause as the prior "orchestrator IS the harness → don't worktree the
brain" finding: the harness is the learnable layer, not a product container.

## Consequence (the artifact this changes)
venture-build's phase-1 SCAFFOLD step (SKILL.md "Create `products/<slug>/`")
and references/artifacts.md must branch on ship-grade-vs-internal:
- ship-grade → `git init` a fresh sibling repo (own LICENSE, releases, public
  remote when CI/billing demands it); the harness keeps only a thin pointer +
  the venture ledger.
- internal/throwaway → the existing `products/<slug>/` tree, unchanged.

## Falsifiable
This ADR is wrong if a future ship-grade venture is successfully shipped
(public repo, releases, its own CI) from inside `products/<slug>/` with no
history/license/billing friction — or if a fresh-repo venture gains nothing a
subdir lacked. Either reopens the decision.
