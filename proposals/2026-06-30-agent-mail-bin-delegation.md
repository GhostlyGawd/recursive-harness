# Agent Mail — the one gated change: thin `bin/harness fleet` → `fleet.cli` delegation

- **Date:** 2026-06-30
- **Status:** PREPARED — awaiting human review/merge via `/harness-pr`. **NOT self-applied**
  (`bin/` is enforcement-PROTECTED; prime directive D5 forbids unilateral edits).
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

## `/harness-pr` checklist (for the human merger)
- [ ] Apply Diff 1 + Diff 2 to `bin/harness` (needs `HUMAN_APPROVED` or `bin/harness approve`).
- [ ] `harness-auditor` on the branch (enforcement-weakening / duplication / provenance check).
- [ ] `/run-evals` (the format change may touch a fleet eval; ADR 0003 in-session replay).
- [ ] Smoke: `harness fleet feed`, `harness fleet claims`, `harness fleet send … / inbox --as …`.
- [ ] Optional follow-ons (separate gated PRs, also prepared in BACKLOG): session-end reaper hook;
      a default-OFF SessionStart `observability.fleet_banner` (count-not-content, pull-not-push).

<!-- provenance: 2026-06-30 autonomous /loop build. Engine+views+CLI+MCP built native-first in
unlocked fleet/ (TDD red→green, 4 view critics + 1 substrate critic + 1 CLI critic, all findings
fixed; dogfooded on the canonical state/ — bin/harness fleet adapter + Mission Control P4 both read
the same shared log). This is the lone enforcement-gated increment; everything else is unlocked. -->
