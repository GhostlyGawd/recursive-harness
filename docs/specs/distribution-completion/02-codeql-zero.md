# CodeQL zero

Phase: 2

Clear the 49 open CodeQL path-injection findings through safe boundary design and
evidence-backed triage, with no bulk dismissal.

## Tasks

- [x] Export alert numbers, locations, dataflow, severity, and live state as the phase
  baseline; group the 27 Cartograph, 15 hook, four eval, and three test findings.
- [x] Identify every trusted root, user-controlled source, normalization step, filesystem
  operation, and intended escape policy before changing runtime code.
- [x] Replace ad hoc path joining with shared fail-closed root/allowlist helpers where the
  security model is identical; preserve intentionally different authorities.
- [x] Fix each reachable flow and individually document any genuine false positive with a
  reproducer and precise dismissal reason.
- [ ] Run extended CodeQL on the PR and query the live API after merge until the open count
  is zero.

## TDD

For each boundary group, add a focused failing exploit/regression before the fix. Tests
must exercise the actual sink and prove benign paths still work. Commit red evidence before
the green implementation.

## Property tests

Generate absolute paths, drive/UNC paths, `..` traversal, mixed separators, Unicode and
percent-like encodings, symlinks/junctions, missing parents, case variants, and root-prefix
collisions. No accepted path may resolve outside its declared authority, including after a
time-of-check/time-of-use transition that the API can prevent.

## BDD scenarios

Given an attacker-controlled artifact name that escapes the configured evidence root
When a Cartograph, hook, or eval workflow reaches a filesystem sink
Then the workflow rejects it without reading, writing, deleting, or executing outside the root

Given a valid nested path inside an allowed root
When the same workflow runs
Then its documented behavior succeeds without weakening the boundary

## Verification gate

Phase 3 cannot advance until all regression and property suites pass, extended CodeQL is
green, every baseline alert has a reviewed resolution, and the live repository reports
zero open CodeQL alerts.

## Completion evidence

- Frozen 49-alert baseline and per-alert resolution table.
- Red/green test commits and shared-boundary design notes.
- Extended CodeQL PR run `29709911883` passed; the first main run `29710058605`
  had a successful Actions analysis but a failed Python upload and was not rerunnable.
  The exact interim receipt is `phase-02-main-scan-retry.json`.
- Live post-merge API receipt showing zero open alerts.
