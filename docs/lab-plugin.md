# Recursive Lab provider package

Recursive Lab is an **experimental**, isolated package for previewing alternative ideas and
measurable roadmaps. It does not change a project, install hooks, read or execute repository code,
contact a network service, or perform tracked-file, issue, pull-request, or message mutations.

## What is included

| Workflow | Input | Output | Evidence | Maturity |
| --- | --- | --- | --- | --- |
| Brainstorm preview | One bounded brief and 2–8 distinct candidates | Deterministic preview envelope plus a user-selection gate | Runtime/property tests and three isolated consumer executions | Experimental; model idea quality and picker behavior unverified |
| Roadmap preview | Brief, measurable win condition, and 1–20 dated milestones | Deterministic preview envelope with no file target | Runtime/property tests and three isolated consumer executions | Experimental; model planning quality and skill selection unverified |
| Exact-target action record | One kind, exact target, and summary | Idempotent preview ID, denial/approval status, or caller-attested receipt | Denial, mismatch, wildcard, unavailable-connector, and receipt tests | Experimental; no mutation executor ships |

Venture Build is excluded because it creates repositories, code, artifacts, Git history, and
potential publication. Build Loop is excluded because it is a production delivery conductor.
Language Selection remains an independent advisory skill rather than a Lab experiment. The full
inventory, owners, side effects, evidence levels, and retirement paths are in the
[Lab capability manifest](../capabilities/lab/capability.json).

## Compatibility status

| Surface | Status | Verified boundary |
| --- | --- | --- |
| Generic Agent Skill | Generated experimental | Self-contained copy executes both previews, denies unavailable mutation, removes cleanly, and preserves project hashes |
| Claude Code CLI | Generated experimental | Fresh isolated user install, both previews, denial, and uninstall pass on 2.1.200 |
| Codex CLI | Generated experimental | Fresh isolated user install, both previews, denial, and uninstall pass on official `@openai/codex` 0.144.6 |
| ChatGPT/Codex hosted web | Unverified | No public claim until personal package execution and persistence rules are proven there |
| Claude Code web | Unverified | No hosted plugin execution claim |
| Model output quality and automatic selection | Unverified | The receipt proves the package/runtime boundary, not that a model will choose it or produce a strong plan |

## Install outside a project

The repository-backed catalog is the tested source channel. It is not a public marketplace listing.
Install at personal/user scope so an established repository keeps its instructions and provider
configuration byte-identical.

```bash
# Codex CLI
codex plugin marketplace add GhostlyGawd/recursive-harness
codex plugin add recursive-lab@recursive-harness

# Claude Code
claude plugin marketplace add GhostlyGawd/recursive-harness
claude plugin install recursive-lab@recursive-harness --scope user
```

For another Agent-Skills-compatible host, copy only
`plugins/recursive-lab/skills/lab/` into its personal skills directory. Do not run the full harness
installer and do not copy the package into a project unless the project owner explicitly wants that
shared artifact.

Remove it with:

```bash
codex plugin remove recursive-lab@recursive-harness
claude plugin uninstall recursive-lab@recursive-harness --scope user
```

Generic hosts remove only the copied personal `lab` directory. Lab has no dependency on another
Recursive package, and uninstall does not touch project files or other plugins.

## Preview a workflow

```bash
python3 <lab-skill>/scripts/lab.py workflow preview --workflow brainstorm \
  --brief "Choose a portable integration" \
  --candidate "Personal plugin::Install outside the repository" \
  --candidate "Reviewed patch::Show one exact optional project change" --json

python3 <lab-skill>/scripts/lab.py workflow preview --workflow roadmap \
  --brief "Distribute safely" \
  --win-condition "Three isolated installs preserve the project hash" \
  --milestone "2026-07-21::Walking skeleton::Generic install passes" --json
```

These commands never create `ROADMAP.md`. They emit JSON to standard output and hold no state.
Supplied text is treated as data and never executed.

## Preview an action; never confuse approval with completion

```bash
python3 <lab-skill>/scripts/lab.py action preview --kind tracked-file \
  --target docs/ROADMAP.md --summary "Save the reviewed roadmap" --json
```

The output binds one exact target and summary to a deterministic request ID. Wildcards and path
traversal fail closed. `action decide --decision approve` reports
`blocked-connector-unavailable`, because the package deliberately ships no connector. A capable host
may separately execute the explicitly confirmed action under its own permissions and then call
`action receipt`; a completed receipt remains caller-attested and says `lab_performed: false`.

## Proof and limitations

The sanitized [consumer receipt](evidence/lab-consumer-acceptance.json) records byte-identical
project hashes, zero repository writes, zero external actions, three package removals, package
hash parity, generic/Claude refresh, and Codex same-catalog reinstall. Lab has no prior version, so
a version-to-version upgrade is truthfully not yet testable. The tests cover malformed and
secret-shaped briefs, adversarial text, duplicate
actions, changed action IDs, oversized roadmaps, wildcard/escaping targets, unavailable connectors,
and interruption residue.

This is not a sandbox and does not constrain a host outside the packaged helper. If a host executes a
confirmed action, that action has the host user's permissions. Rebuild with
`python3 scripts/build_lab_plugins.py`; verify source and package closure with
`python3 scripts/build_lab_plugins.py --check`.

<!-- provenance: 2026-07-20 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-045 Phase 6 experimental Lab package and real consumer acceptance. -->
