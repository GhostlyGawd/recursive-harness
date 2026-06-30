# Agent Mail — the one gated change: thin `bin/harness fleet` → `fleet.cli` delegation

- **Date:** 2026-06-30
- **Status:** APPLIED under explicit human grant (2026-06-30) — see `## Approval`. The diffs below
  are committed on branch `feat/2026-06-30-agent-mail`; a human still performs the binding PR merge.

## Approval

`bin/` is enforcement-PROTECTED (`hooks/guard_enforcement_layer.py` PROTECTED tuple includes
`"bin"` and `".github"`); prime directive D5 forbids unilateral edits. The repo owner authorized
these enforcement-layer edits (`bin/harness` + `.github/workflows/ci.yml`) with the verbatim grant,
in session on 2026-06-30:

> **Merge all**

The grant was recorded via `bin/harness approve` (logged to `state/approvals.jsonl`, which is
gitignored); the marker was placed for **only** these edits and **revoked immediately after each**.
This committed quote is the durable grant evidence for the merging human, since the approvals
ledger is machine-local and never reaches the PR.
- **Context:** Agent Mail's engine + 3 views + CLI + MCP adapter shipped native-first in the
  UNLOCKED `fleet/` tree (132 tests green, 6 critic passes, dogfooded on the canonical log). This
  is the **single** locked change the whole build needs — and after it, every future view ships
  with ZERO further `bin/harness` edits (the delegation forwards the full surface).

## What changes

`bin/harness fleet` today (Phase 2) hand-rolls `emit|feed|reap` inline. Replace that with a
paper-thin forwarder to the richer, unlocked `fleet.cli` (which adds `claims|unit|send|inbox|ack|
release`, scannable output, `--set/--note`, `--json`, the overview). The ONE canonical Option-A
resolver (`_resolve_state_dir`) is injected — no second resolver (D6).

### Diff 1 — `cmd_fleet` (replace the body, ~bin/harness:591-636)
```python
def cmd_fleet(args) -> int:
    """Lateral-coordination channel. Thin adapter: inject the ONE canonical state dir, then
    delegate to the unlocked, stdlib-only fleet.cli (full view surface). Adding a view needs no
    further bin/harness edit. See proposals/2026-06-22-agent-mail-product.md + fleet/pm/specs/ARCHITECTURE.md."""
    sys.path.insert(0, ROOT)  # fleet/ lives at the repo root
    try:
        from fleet import cli as fleet_cli
    except ImportError as exc:
        print(f"fleet engine unavailable: {exc}", file=sys.stderr)
        return 1
    return fleet_cli.main(["--state-dir", _resolve_state_dir(), *args.rest])
```

### Diff 2 — the subparser (replace bin/harness:768-778)
```python
    sp = sub.add_parser("fleet",
                        help="Agent Mail — coordination channel (feed|emit|claims|unit|send|inbox|ack|release|reap)")
    sp.add_argument("rest", nargs=argparse.REMAINDER,
                    help="forwarded verbatim to `python -m fleet` (run `harness fleet --help` for actions)")
    sp.set_defaults(fn=cmd_fleet)
```
(`argparse` is already imported in `bin/harness`.)

## Why this shape

- **Buys all remaining views for one human round-trip.** `REMAINDER` forwards any action +
  flags, so `claims`, `unit`, `send`, `inbox`, `ack`, `release` — and anything added later — work
  with no further locked edit. (ARCHITECTURE decision #5.)
- **One resolver (D6).** `_resolve_state_dir()` stays the sole Option-A implementation; `fleet.cli`
  takes the path injected, never resolves it.
- **Strictly an improvement to existing behavior.** `harness fleet feed|emit|reap` keep working;
  output becomes the scannable `fleet.render` format (relative age, TTL, `k=v`, not raw dict repr).

## Tradeoffs to weigh in review

- `REMAINDER` loosens `bin/harness`'s own arg-validation for the `fleet` namespace — validation
  moves into the unlocked `fleet/cli.py` (where it iterates freely). Acceptable: the locked surface
  becomes a pass-through.
- Output format for `harness fleet feed` changes (improvement, but a contract change). Any eval
  asserting the OLD dict-repr format must be updated. **Run `/run-evals` before merge.**

## `/harness-pr` checklist
- [x] Apply Diff 1 + Diff 2 to `bin/harness` (under the grant above; committed `8b1b8c1`).
- [x] Wire the 6 stdlib-only fleet suites into `.github/workflows/ci.yml`; excuse `test_mcp` (mcp dep)
      — `test_ci_coverage` requires it (committed `1d4c43f`).
- [x] `harness-auditor` on the branch → substance clean (no enforcement weakening / duplication /
      second resolver / reward-hacking); sole must-fix was this `## Approval` quote, now added.
- [x] Proportionate eval check: the two fleet-adjacent evals (`cli-cp1252-output`,
      `mission-control-p2p5`) pass; no eval asserts the old `fleet feed` format; `lint_harness.py` clean.
- [x] Smoke: `harness fleet feed | claims | unit | inbox | emit | reap` verified on the canonical state.
- [ ] **Human:** review + merge the PR (the binding gate); the format change is intended.
- [ ] Optional follow-ons (separate gated PRs, in BACKLOG): session-end reaper hook (B-01); a
      default-OFF SessionStart `observability.fleet_banner` (UX-P4, count-not-content, pull-not-push).

<!-- provenance: 2026-06-30 autonomous /loop build. Engine+views+CLI+MCP built native-first in
unlocked fleet/ (TDD red→green, 4 view critics + 1 substrate critic + 1 CLI critic, all findings
fixed; dogfooded on the canonical state/ — bin/harness fleet adapter + Mission Control P4 both read
the same shared log). This is the lone enforcement-gated increment; everything else is unlocked. -->
