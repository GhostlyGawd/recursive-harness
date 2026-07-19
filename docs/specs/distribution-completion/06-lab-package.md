# Lab capability package

Phase: 6

Package experimental brainstorm, roadmap, venture, and other incubation workflows without
allowing experiments to inherit production claims or hidden mutation authority.

## Tasks

- [ ] Inventory candidate Lab workflows and exclude any surface lacking an owner, safety
  class, explicit inputs/outputs, side-effect policy, and retirement path.
- [ ] Mark the entire package experimental and label each workflow's provider support and
  evidence level independently.
- [ ] Make analysis preview-first; require explicit targets and confirmation for tracked
  files, issues, pull requests, messages, or other external mutations.
- [ ] Isolate Lab state and dependencies from core packages so uninstalling Lab cannot
  damage Observe, Learn, Verify, Coordinate, or Guard.
- [ ] Validate install, upgrade, and uninstall in consumers with existing tools and docs.

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

- Included/excluded workflow inventory and rationale.
- Package/manifest receipts and dependency graph.
- Preview, confirmation, denial, interruption, upgrade, and uninstall captures.
- Before/after consumer hashes and external-side-effect audit.
- Honest provider and maturity matrix merged into documentation.
