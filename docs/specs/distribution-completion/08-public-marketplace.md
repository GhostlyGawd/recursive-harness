# Public marketplace submission

Phase: 8

Submit the verified skills-only distribution to the actual public OpenAI marketplace
process, then prove a fresh consumer can discover and install the published listing.

## Tasks

- [ ] Reconfirm current official submission requirements and account eligibility immediately
  before submission; record source, date, identity, and permissions without exposing secrets.
- [x] Build the final skills-only bundle from the released commit with name, description,
  brand assets, support, privacy, terms, version, canonical-source, and receipt metadata.
- [x] Validate least privilege, zero embedded credentials/private data, prompt-injection
  resistance, declared side effects, uninstall, and all public claims.
- [x] Prepare exactly five positive and three negative evaluator test cases for each submitted
  item, covering intended triggers, non-triggers, safety boundaries, and existing-project coexistence.
- [ ] Submit through the official portal, retain the submission/review receipt, answer review
  findings through reviewed changes, and publish only after acceptance.
- [ ] From a fresh external consumer with no repository-local catalog, discover, install,
  execute, upgrade, and uninstall the public listing.

## TDD

Add a submission-bundle validator first and capture failures for missing metadata, wrong test
counts, mutable/unreceipted source, unsafe permissions, private strings, and false marketplace
claims. Drive the final archive and submission record from that contract.

## Property tests

Generate names/descriptions/fixtures with Unicode, markup, URL variations, secret-like values,
instruction injection, path traversal, and duplicated test cases. Validation must fail closed,
keep all links canonical and public, and ensure evaluator cases remain distinct and classified.

## BDD scenarios

Given a fresh supported consumer that has never opened the Recursive repository
When the user searches the public marketplace and selects Recursive Observe
Then the official listing is discoverable and installs a receipt-matching released package

Given a prompt resembles Recursive terminology but requests an unsafe or unrelated action
When marketplace evaluation selects a skill
Then the negative case does not trigger or mutate state and explains the supported boundary

## Verification gate

Phase 9 cannot advance until official review is accepted, the owner publishes the listing,
all public metadata resolves, and a fresh external install/execute/upgrade/uninstall journey
passes without a local catalog, checkout, or broken link.

## Completion evidence

- Dated official-requirement and eligibility receipt.
- Validated submission bundle, public asset hashes, and permission/privacy scan.
- Exactly five positive and three negative evaluator cases and their results.
- Submission, review, response, acceptance, and publication identifiers.
- Fresh external discovery/install/execution/upgrade/uninstall transcript.

## Pre-submission evidence

The tracked [`marketplace/recursive`](../../../marketplace/recursive/README.md) input records
the official requirements observed on 2026-07-20, exact listing copy, public legal/support
URLs, four starter prompts, exactly five positive and three negative evaluator cases, release
notes, and an explicit preflight—not-public state. `scripts/build_public_plugin.py` reconstructs
the four-skill package from tag `v0.1.2` at commit `5a524d1`, verifies each provider receipt,
rejects unsafe metadata and archive members, and builds byte-identical ZIPs.

[`public-plugin-preflight.json`](../../evidence/public-plugin-preflight.json) records a real
official Codex CLI 0.144.6 local-catalog install of that exact ZIP, all four deterministic
runtime journeys, zero writes to a foreign repository with existing agent configuration,
package removal, and preservation of private sidecar state. It deliberately records public
discovery, hosted execution, and model skill selection as untested. Portal eligibility,
submission, review, publication, and the no-local-catalog consumer gate remain open.
