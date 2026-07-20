# Lab capability package

Phase: 6

Status: implementation complete; protected-main receipt pending

Package experimental brainstorm, roadmap, venture, and other incubation workflows without
allowing experiments to inherit production claims or hidden mutation authority.

## Tasks

- [x] Inventory candidate Lab workflows and exclude any surface lacking an owner, safety
  class, explicit inputs/outputs, side-effect policy, and retirement path.
- [x] Mark the entire package experimental and label each workflow's provider support and
  evidence level independently.
- [x] Make analysis preview-first; require explicit targets and confirmation for tracked
  files, issues, pull requests, messages, or other external mutations.
- [x] Isolate Lab state and dependencies from core packages so uninstalling Lab cannot
  damage Observe, Learn, Verify, Coordinate, or Guard.
- [x] Validate install, same-version refresh/reinstall, and uninstall in consumers with existing
  tools and docs. This is the first Lab version, so no prior-version upgrade can yet be claimed.
- [ ] Merge the exact package and consumer receipt through protected checks and record the live
  protected-main and CodeQL receipt.

## TDD

Create a failing package contract for experimental labeling, dependency isolation,
preview-before-action, exact external target disclosure, receipt closure, and clean
uninstall. Add one red user-journey contract per included workflow.

## Property tests

Generate malformed briefs, adversarial repository text, large roadmaps, unavailable
connectors, duplicate actions, and interrupted operations. Lab must not execute instructions
from untrusted content, expand its target set, or leave an untracked partial mutation.

## BDD scenarios

Given a user installs only Recursive Lab into an established project
When a brainstorm workflow produces a proposed roadmap
Then the output remains a preview and existing project files are unchanged

Given an experiment requests an external action and the connector is unavailable
When the user declines or the action fails
Then Lab reports no completed action and retains a safe retry or discard path

## Verification gate

Phase 7 cannot advance until each shipped experiment has red/green journey evidence, the
package is isolated and cleanly uninstallable, mutation-denial and interruption properties
pass, and all public surfaces say experimental.

## Completion evidence

- Included/excluded workflow inventory, owners, safety classes, provider support, evidence, and
  retirement paths: `capabilities/lab/capability.json`.
- Reproducible package and dependency-free manifest receipt:
  `plugins/recursive-lab/canonical-source.json` and `scripts/build_lab_plugins.py --check`.
- Red-first example, property, and BDD coverage for preview, exact-target confirmation, denial,
  interruption, caller-attested receipt closure, and clean removal: `tests/test_lab_package.py`.
- Fresh generic, Claude Code 2.1.200, and official Codex 0.144.6 isolated install, refresh/reinstall,
  preview, unavailable-connector, and uninstall journeys:
  `docs/evidence/lab-consumer-acceptance.json`.
- Byte-identical existing-project hashes, zero repository writes, zero external actions, and honest
  unsupported model/hosted/version-upgrade claims: `docs/lab-plugin.md`.
- Live protected-main and CodeQL receipt: pending merge of this exact implementation.
