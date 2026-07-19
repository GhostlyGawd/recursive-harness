# Specialization provider contract

Specialization is a canonical Recursive Harness capability. Provider adapters
package its runtime and translate lifecycle events; they do not own independently
editable copies.

## Capability contract

The first observation of a reusable `gap`, `correction`, or `improvement` must:

1. Append one sanitized evidence event.
2. Create or update one private candidate workspace.
3. Preserve the provider session and turn identity without storing a transcript.
4. Prompt the active agent to author and dogfood that candidate during the task.

Promotion is proof-gated. A candidate becomes `validated` after a worked dogfood
replay with concrete verification; new capabilities must also show that the
procedure generalizes. Recurrence counts distinct `provider:session` pairs and
raises review urgency, but it neither proves a candidate nor delays a verified
correction. New evidence reopens the candidate as a new revision, so proof from
an earlier revision cannot validate an amendment silently.

## Public event fields

Every JSONL event carries `schema_version`, `event_id`, `ts`, `kind`, `domain`,
and `domain_key`. Evidence adds `learning_kind`, `shape`, `provider`, `session`,
`turn`, optional target-skill provenance, category, and facet tags. Candidate and
dogfood events record lifecycle status and verification receipts.

The contract intentionally excludes full prompts, transcripts, authentication
material, and raw external content.

## State contract

Local adapters use one provider-neutral state directory:

| Platform | Default |
| --- | --- |
| Windows | `%LOCALAPPDATA%\RecursiveHarness\specialization\` |
| macOS | `~/Library/Application Support/RecursiveHarness/specialization/` |
| Linux | `${XDG_STATE_HOME:-~/.local/state}/recursive-harness/specialization/` |

`RECURSIVE_HARNESS_STATE_HOME` overrides the parent; the runtime appends
`specialization/`. State is sanitized, process-serialized, atomically replaced,
and constrained to the current user where the host filesystem supports it.

The `migrate` command idempotently imports the former checkout-local
`state/skill_needs.jsonl`, activates private candidates for open imported needs,
and leaves the source untouched.

## Adapter contract

An adapter must:

- package byte-equivalent `needs.py`, `private_state.py`, and the shared evidence
  reference, verified by `scripts/build_codex_specialization_plugin.py --check`;
- pass the canonical ledger tests and provider lifecycle fixtures;
- inject exact provider/session/turn identity into the active agent;
- fail open on malformed hook input or unavailable local state;
- document runtime prerequisites, lifecycle gaps, installation, trust, upgrade,
  removal, and retained state; and
- identify generated source with `canonical-source.json`.

The Claude adapter uses its existing skill and Stop lifecycle integration. The
Codex adapter additionally maps `SessionStart`, `UserPromptSubmit`, and `Stop`.
Neither adapter mines historical transcripts. ChatGPT/Codex Memories may provide
helpful context but are not part of this contract.

provenance: 2026-07-18, provider boundary extracted while building the first
OpenAI/Codex Specialization adapter from the canonical Recursive implementation.
