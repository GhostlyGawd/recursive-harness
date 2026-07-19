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

A `correction` or `improvement` must identify its target skill, canonical
provenance, and a readable source `SKILL.md`; an adapter must not fall back to a
new generic expert when those amendment inputs are absent or the target name does
not match the source frontmatter. The source input must resolve to a literal
`SKILL.md`; a `gap` cannot carry owner inputs.

When later evidence proves that a generic gap belongs to an existing skill, the
candidate must archive its prior draft and rebase from the named source. Once a
candidate is bound to one target skill, a different target for the same domain is
rejected before evidence is written; adapters never relabel content silently.
That rejection also applies to targetless gap evidence for a bound domain, which
must not clear the owner and create an indirect owner-change path.

Promotion is proof-gated. A candidate becomes `validated` after worked dogfood
with concrete verification; a new capability requires two distinct worked cases
for its current revision and must show that the procedure generalizes. Recurrence
counts distinct `provider:session` pairs and
raises review urgency, but it neither proves a candidate nor delays a verified
correction. New evidence reopens the candidate as a new revision, so proof from
an earlier revision cannot validate an amendment silently.

## Public event fields

Every JSONL event carries `schema_version`, `event_id`, `ts`, `kind`, `domain`,
and `domain_key`. Evidence adds `learning_kind`, `shape`, `provider`, `session`,
`turn`, category, and facet tags; target-skill provenance is required for
corrections/improvements and omitted for new gaps. Candidate and dogfood events
record lifecycle status and verification receipts.

The contract intentionally excludes full prompts, transcripts, authentication
material, and raw external content.

## State contract

Local adapters use one fixed provider-neutral state directory:
`~/.recursive-harness/specialization/`. The runtime accepts no state-path argument or
environment override, and candidate directory names are derived with SHA-256 rather than
free-form evidence. A capability-wide interprocess transaction serializes compound
ledger, manifest, migration, validation, and nudge transitions. State is sanitized,
atomically replaced, and constrained to the current user where the host filesystem
supports it.

The `migrate --from-path <checkout>/state/skill_needs.jsonl` command idempotently
imports an explicitly named former checkout-local ledger, activates private
candidates for open imported needs, and leaves the source untouched. Provider
packages never guess a checkout path. Migration accepts only a literal
`state/skill_needs.jsonl`, discards legacy candidate paths, and rebuilds candidate
identity from a compact single-line domain before any filesystem access. A domain
containing correction or improvement evidence is quarantined because migration
cannot prove its source `SKILL.md`; re-record it through the provenance owner.

## Adapter contract

An adapter must:

- package the canonical `needs.py` with only its local storage-module import rewritten,
  a byte-equivalent `private_state.py` under the collision-resistant
  `specialization_state.py` name, and the shared evidence reference;
- bind every manifest, hook, skill file, runtime, reference, and license in the generated
  package receipt and reject missing, changed, or unexpected payloads with
  `scripts/build_codex_specialization_plugin.py --check`;
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
