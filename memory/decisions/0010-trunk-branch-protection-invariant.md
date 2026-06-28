# ADR 0010: Branch protection on `main` is a required, non-repo-captured invariant

date: 2026-06-28
status: accepted
provenance: 2026-06-28, session c6521109. User opened a session having discovered that
PRs failing CI/lint had merged into `main` ("why have we been merging prs that are failing
ci and lint ... how has that been allowed"). RCA: PR #169 added a test unwired into ci.yml
→ `test_ci_coverage` went red → it merged anyway; #170/#171/#174/#176 then inherited the
same red and each merged on top of it (~2h) until #177 greened main. Two gaps: `main` had
ZERO branch protection (`Branch not protected`, HTTP 404) AND no harness-side pre-merge
check. Fixed both this session: protection enabled (this ADR records it) + a local hook
(`hooks/pre_merge_ci_gate.py`, PR #182).

## Context
CI (`harness-ci` / `lint-and-test`) ran on every PR but was purely **advisory**: nothing
refused a red merge. The `pre_merge_ci_gate` hook is the fast local catch, but it travels
with a clone only as *code* — and it fails open and has a deliberate hatch. The only thing
that BINDS a merge regardless of who runs it, whether the hook is installed, or whether the
hook was hatched, is **GitHub server-side branch protection**. That protection is not a
repo artifact, so a fresh clone, a fork, a re-created repo, or an accidental "disable
protection" silently re-opens the exact hole this session closed.

## Decision
`main` MUST carry branch protection with these settings; treat it as a standing invariant,
not a one-time fix:

- required status check: **`lint-and-test`**
- **`strict: true`** — the branch must be up to date with `main` before merge (this also
  stops the stale-base red-inheritance that drove the #170–#176 cascade)
- **`enforce_admins: true`** — LOAD-BEARING. This is a solo-owner repo, so the admin IS
  the merging actor (including the harness merging on a standing grant). With
  admin-bypass (`enforce_admins: false`) the gate is toothless against the only person who
  merges. The emergency escape is deliberately *disabling protection*, not a standing
  bypass flag. (This session first set `false`, then corrected to `true` for exactly this
  reason.)

Re-apply command (run from the repo; restores the invariant after a clone/fork or an
accidental disable):

    gh api -X PUT repos/:owner/:repo/branches/main/protection --input - <<'JSON'
    {
      "required_status_checks": { "strict": true, "contexts": ["lint-and-test"] },
      "enforce_admins": true,
      "required_pull_request_reviews": null,
      "restrictions": null
    }
    JSON

Verify: `gh api repos/:owner/:repo/branches/main/protection --jq
'{required: .required_status_checks.contexts, strict: .required_status_checks.strict,
admins: .enforce_admins.enabled}'`.

## Why this is recorded as a decision, not just "done"
The config APPLICATION is live, but config that lives only on GitHub is invisible to the
trunk and undiscoverable to a future session or a fork. Versioning the requirement + the
re-apply command here makes the invariant portable and auditable. Pairs with ADR 0003
(`lint-and-test` is pure-Python CI, the thing being required) and `hooks/pre_merge_ci_gate.py`
(the local fast-feedback layer — defense in depth, NOT a substitute for the server wall).

## Cost accepted
`enforce_admins: true` + `strict: true` means even the owner cannot merge a red or stale
PR without first lifting protection — by design. A genuine emergency merge is a two-step
deliberate act (disable protection, merge, re-enable), which is the intended friction.
