# Lab security and privacy boundary

- Safety class: experimental.
- Repository access: none in the packaged runtime.
- Repository writes: none.
- Private state: none.
- Credentials: never requested or discovered.
- Network and connectors: none.
- Automatic hooks or events: none.
- Supplied briefs, candidates, milestones, summaries, targets, and evidence are untrusted data and
  are never executed.
- Common secret-shaped markers, control characters, oversized fields, path traversal, and wildcard
  targets fail closed without echoing the rejected value.
- Action IDs bind the action kind, exact target, and summary. Repeating the same preview is
  idempotent; changing any field invalidates the ID.
- A `caller-attested-completed` receipt is an external assertion, not independent verification and
  not a claim that Lab performed an action.
- No sandbox claim is made. If a host performs a confirmed action, it runs under that host's own
  permissions and security model.

The package contains no Observe, Learn, Verify, Coordinate, Guard, venture, build-loop, provider
configuration, or project instruction files. Removing its package directory cannot remove or alter
those surfaces.

<!-- provenance: 2026-07-20 P-2026-045 Phase 6. -->
