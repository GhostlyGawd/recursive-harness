# Recursive Harness vs. Agentic Dev OS

**Observed:** 2026-07-17

**Recursive Harness:** `d8939b3b4aa5fe9be4c1502893578bbdb86d9fbe`

**Agentic Dev OS:** `22523bc78b7d65a4a90b9b01d08b681591fc662f`

This is a point-in-time product comparison, not a portfolio reclassification. Live GitHub
settings, repository contents, and the governed `repo-audit` inventory were checked at the
commits above.

## Verdict

**Recursive Harness is the better operational harness today.** It has an installed Claude
Code runtime, lifecycle hooks, private state ledgers, prediction calibration, corrections,
evaluations, concurrency guards, tests, and an operator surface. It is a beta product used
as a working control plane rather than only a contract.

**Agentic Dev OS is the better formal governance reference.** Its explicit chain from
outcome through opportunity, bet, PRD, specification, ticket, code, test, event, metric,
and review is stronger for team traceability. It also has stable IDs, bidirectional links,
risk tiers, digest-bound approvals, scoped changes, archival rules, telemetry contracts,
and a repository-wide MIT license.

There is no useful universal winner: Recursive Harness wins the job of operating and
improving a Claude Code environment; Agentic Dev OS wins the job of specifying a formal,
portable product-delivery governance model.

## Evidence matrix

| Dimension | Recursive Harness | Agentic Dev OS | Better fit |
| --- | --- | --- | --- |
| Live agent runtime | Hooks, commands, skills, ledgers, Fleet, Mission Control | Primarily contracts and CLI-backed governance records | Recursive Harness |
| Feedback learning | Prediction scoring, correction capture, retrospectives, eval replay | Metrics and review chain, but less runtime calibration depth | Recursive Harness |
| Safety boundaries | Protected enforcement layer, guarded worktrees/sessions, required CI | Risk and scope policy are formalized; live branch protection was absent when observed | Split |
| Product traceability | Decisions, proposals, provenance, tests | Stable cross-artifact IDs and bidirectional product chain | Agentic Dev OS |
| Portability proof | Source install and real Claude Code integration | Portable contract exists, but no independent installer/adoption proof was observed | Recursive Harness today |
| Repository hygiene | Public beta, protected main, security tooling; no root license | Public lab, MIT license, pinned workflows, clean observed alert state | Split |
| Complexity cost | Large operational surface with accumulated history | Cleaner formal model, but the full product chain is heavyweight for small harness changes | Context-dependent |

## Recommended adoption map

Adopt into Recursive Harness:

1. Stable proposal IDs that survive file moves and title changes.
2. Separate decision state from implementation state.
3. Require evidence for terminal transitions and keep an append-only status history.
4. Separate active work from resolved history and generate a current index.
5. Borrow risk/scope language only for changes where it improves review clarity.

Do **not** import the entire PRD/spec/ticket hierarchy. Recursive Harness already has a
smaller learning loop; forcing every correction or harness proposal through a full product
chain would add friction without improving its core evidence.

Potential future learnings for Agentic Dev OS—prediction calibration, correction-to-
guardrail promotion, and interactive evaluation replay—should be proposed there only with
an acceptance test and validation in at least two consumers. This comparison makes no such
cross-repository change.

## Gaps that affect the verdict

- Recursive Harness has no repository-wide license and retains a static-analysis triage
  backlog. Its security assessment documents these limitations.
- Agentic Dev OS was classified as an active lab and candidate-not-canonical in the observed
  governance registry. Its portable-contract ambition lacks release, package, independent
  five-minute proof, migration, and production adoption evidence at the observed commit.
- Live controls can change without a commit. At observation time, Recursive Harness main
  required current `lint-and-test` with administrator enforcement; Agentic Dev OS main was
  not protected.

The practical recommendation is therefore to continue building Recursive Harness as the
working product while selectively adapting Agentic Dev OS's governance strengths through
reviewed, locally proven changes.
