# Agent Mail — Bugs

Defects found during build-review-validate. Every bug gets a row before it gets a fix, so
recurrence is visible. Pairs with the `auto-healer` skill for cross-session bug memory.

Format:
```
### BUG-<n> — <one-line title>  [open|fixed]
- Found: <date / iteration / which review lens>
- Repro: <smallest steps or failing test name>
- Cause: <root cause once known>
- Fix: <commit / test that now guards it>
```

---

## Open risks (not yet bugs — design hazards to guard with tests)

### RISK-1 — global ring-buffer cap SILENTLY evicts an unread postbox message  [FIXED by R3.5]
- **Resolution (R3.5):** `reap` now evicts DISPOSABLE kinds (note/progress) before
  CRITICAL_KINDS (handoff/ack/claim/release); criticals still bounded at `cap`. Substrate tests
  `test_reap_cap_protects_critical_kinds` + 2 more, and the flipped
  `test_flood_does_not_evict_unacked_handoff_R35` (now asserts survival), plus an e2e flooding 5000+
  disposables. A directed handoff is no longer silently lost under disposable-stream pressure.
  (History below kept for provenance.)
- Found: 2026-06-30 / Architecture lens (R-CAP); CONFIRMED + sharpened by R3 critic (verified probe:
  1 critical handoff + 6000 notes → handoff evicted, `inbox` empty, `unread_count==0`).
- Detail: `reap`'s 5000-record cap (`eventlog.py:106`) is shared across feed+claims+units+postbox.
  A chatty `progress`/`note` stream evicts the oldest records, which can be a critical unacked
  `handoff` → silent loss.
- ⚠️ Correction: the earlier "surface `unread_count` so loss is detectable" mitigation is FALSE —
  `unread_count == len(inbox)`, so eviction zeroes the signal. No cheap detection exists.
- Status: pinned by `test_flood_evicts_unacked_handoff_RISK1` (asserts the current silent-loss
  behavior). Durable fix = a **per-kind cap floor** in `reap` → promoted to roadmap **R3.5**
  (next build). Accepted limitation for low-volume harness use until then.

### RISK-2 — read-once (`ack`) is global, not per-embodier  [open]
- Found: 2026-06-30 / Architecture lens (R-OWNER).
- Detail: `ack`→supersede tombstones a handoff for everyone. Correct for single-owner directed
  delivery; WRONG for fan-out broadcast. Document postbox as single-owner; broadcast out of scope.

### RISK-3 — `handoff` kind is read by BOTH unit-doc and postbox  [open → mitigated by design]
- Found: 2026-06-30 / Architecture lens (R-HANDOFF).
- Mitigation: `@`-namespace convention is load-bearing — handles start with `@` (`_handle`
  normalizes), unit ids never do; `unit_records` filters `target==unit` (exact) so they never cross.
  Guard with a test in both `test_units.py` and `test_postbox.py`.

---

## Implementation bugs

### BUG-1 — `targets_overlap` misses literal-dir-vs-glob (false negative)  [fixed]
- Found: 2026-06-30 / iteration 2 / R1 critic review.
- Repro: `targets_overlap("src/", "src/**")` → `False` (should be `True`); likewise
  `("src","src/api/**")`, `("src","src/*")`, `("src/api","src/api/**")`. Incident:
  `overlap_pairs([claim "src/", claim "src/api/**"])` returned 0 pairs — a silently missed
  conflict, the exact 3-in-48h clobber class, and the false-NEGATIVE direction ARCHITECTURE
  decision #4 forbids.
- Cause: the literal-vs-glob branch was pure `fnmatch(literal, glob)`, which fails when the
  literal is a *parent directory* of the glob's subtree (`fnmatch("src","src/**")==False`).
- Fix: that branch now ALSO tests segment-prefix containment of the literal's segments against
  the glob's `_literal_prefix`. New failing tests added first (truth-table rows +
  `test_overlap_dir_owner_vs_glob`), then `fleet/claims.py` fixed → green.

### BUG-2 — `resource_claims` order-dependent on a `ts` tie  [fixed]
- Found: 2026-06-30 / iteration 2 / R1 critic review.
- Repro: two live claims, same `target`, same `ts`, different actors: `[a,b]`→t1 wins,
  `[b,a]`→t2 wins. Contradicted the "Pure; order-independent" docstring; `now_s` is injectable
  so `ts` CAN collide (the docstring's "engine keeps them distinct" was an overclaim).
- Cause: strict `e["ts"] > cur["ts"]` with no secondary key.
- Fix: compare `(e["ts"], e["id"])` (id is the deterministic tiebreak, per TESTPLAN §0);
  docstring corrected. New failing `test_resource_claims_tie_break_deterministic` added first.

### Also added (test-net gaps the critic flagged): TESTPLAN §1 `test_p2_reap_idempotent`,
`test_p3_monotone_expiry` (applied to `live_claims` — the dedup'd winner can legitimately switch
to a shadowed-but-live claim, so monotonicity is a property of the live SET), and
`test_c2b_overlap_symmetric_over_dir_and_glob_forms`.

### BUG-3 — CLI output crashed on a cp1252 (Windows) console  [fixed — two passes]
- Found: 2026-06-30 / iter 6 (chrome) + iter 7 R5 critic (user content).
- Repro (pass 1): render/cli CHROME used `→ · — … ⚠ ⇄` glyphs → `UnicodeEncodeError`.
- Fix (pass 1): ASCII-folded all source strings in `render.py` + `cli.py`.
- Repro (pass 2, R5 critic): USER-supplied payload (`--note "☃"`, smart quotes, `→`) still flowed to
  `print()` unescaped → crashed `feed`/`inbox`/`unit`, and `--json` with `ensure_ascii=False` too.
- Fix (pass 2): `_harden_stream()` reconfigures stdout/stderr to `errors="backslashreplace"` at the
  top of `main()` (non-encodable user glyphs render as `\uXXXX`, never crash); dropped all three
  `ensure_ascii=False`. Guard: `test_cli.test_cli_survives_non_ascii_user_content_on_cp1252` (forces a
  cp1252-strict stream with `→ ☃ "smart"` through feed/claims/inbox/unit + `--json`).
- Lesson: in-process tests capture stdout via StringIO (UTF-8) so they never hit the console codec;
  the first fix only covered chrome — the critic's adversarial probe with USER content found the rest.

### BUG-4 — re-exporting `units` fn shadowed the `fleet.units` submodule  [fixed]
- Found: 2026-06-30 / iter 6 / R5 real e2e.
- Repro: `__init__.py` did `from .units import units`, rebinding the package attr `units` from the
  SUBMODULE to the function; `cli.py`'s `from . import units as ud` then bound to the function →
  `AttributeError: 'function' object has no attribute 'read_unit'`.
- Fix: re-export as `live_units`. Guard: `test_cli.test_package_surface_units_is_module`.
