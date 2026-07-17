# Operations

## Daily task loop

Start a non-trivial task with an expectation that can be proven wrong:

```bash
python3 bin/harness predict \
  --task "fix the failing parser" \
  --expect "the malformed fixture is rejected and the full parser suite stays green" \
  --confidence 0.75 \
  --category debugging
```

Use the returned identifier when the outcome is known:

```bash
python3 bin/harness outcome PREDICTION_ID --result hit --notes "fixture and suite passed"
```

Use `--result miss` when any material clause failed. A candid miss improves calibration;
an unscored result only creates debt.

## Session and maintenance cadence

| Cadence | Action | Purpose |
| --- | --- | --- |
| After significant or correction-born work | `/retro` | Review signals and route durable lessons |
| After a recurring accepted task | `/capture-eval` | Preserve a privacy-safe regression case |
| On the default five-session cadence | `/calibrate`, then `/gc` | Score debt, inspect calibration, and roll old hot state into cold summaries |
| Monthly or before a major autonomy decision | `/meta-retro` | Audit use, rot, eval coverage, and acceptance evidence |
| After structural changes | `/atlas` | Refresh the generated Atlas and Pulse |
| At session end (automatic, fail-open) | Private-state scrub | Expire raw correction/failure excerpts past the configured window |

The active cadence and feature flags are inspectable:

```bash
python3 bin/harness features
python3 bin/harness stats
python3 bin/harness skill-stats --days 30
python3 bin/harness privacy audit --json
```

Soft observability features can be disabled locally without changing the repository. For
example:

```bash
python3 bin/harness features set observability.log_corrections false
python3 bin/harness features set observability.heal_autocapture false
```

Safety-critical guard keys ignore local overrides. Their committed values require the
enforcement-change workflow.

Raw correction and failure excerpts default to 30-day retention. Preview and apply an
explicit scrub with:

```bash
python3 bin/harness privacy scrub
python3 bin/harness privacy scrub --apply
```

The scrub preserves record metadata and counts; it sanitizes legacy rows and replaces only
expired raw excerpt fields. Adjust `privacy.correction_excerpt_retention_days`,
`privacy.failure_excerpt_retention_days`, or `privacy.scrub_on_session_end` with the normal
soft-feature command when local policy requires different per-class windows or manual-only
cleanup. `privacy scrub --days N` deliberately overrides both windows for one run.

## Diagnostics

```bash
python3 bin/harness doctor
python3 bin/harness scorecard
python3 bin/harness health
python3 cartograph/extract.py --audit
python3 cartograph/extract.py --check
```

- `doctor` diagnoses installation and account-pin problems with a concrete fix.
- `scorecard` summarizes predictions, tests, autonomy, skill value, and bug memory.
- `health` reports a structural score; it is advisory, not a target to game.
- Cartograph's audit identifies review candidates; `--check` blocks new structural rot.

For a focused architecture question:

```bash
python3 bin/harness ask --context commands/retro.md
python3 bin/harness ask dependents hook:guard_enforcement_layer
python3 bin/harness ask path command:retro skill:routing-learnings
```

## Account and settings maintenance

After pulling a change to `templates/account-settings.json`, the installed `post-merge` Git
hook runs:

```bash
./account-init.sh --all --sync-settings
```

Run that command manually if the hook was not installed or reports a failure. Each live
settings file is backed up before regeneration. Put per-account deviations in the ignored
`overrides.json`, not in generated `settings.json`.

If accounts have separate populated `projects/` session stores, stop all affected Claude
Code sessions before consolidation:

- Windows: `./sync-account-sessions.ps1 <account>` from PowerShell
- Unix-like: `./sync-account-sessions.sh <account>` from Bash

The scripts merge without silently overwriting forked transcripts and park backups before
cutover.

## Concurrency and worktrees

The harness coordinates three distinct risks:

- A worktree may have one live owner at a time.
- A session cannot write into another live worktree without an explicit one-command hatch.
- Trunk-changing operations use a shared lease so concurrent PR flows do not race.

When parallel work is legitimate, create a separate Git worktree and branch. Do not disable
the guards as a routine workflow. If a dead session left ownership behind, wait for the
configured TTL or use the documented release/recovery path printed by the guard.

Fleet provides append-only coordination rather than a shared mutable scratchpad:

```bash
python3 bin/harness fleet emit claim --target src/auth.py --note "refactoring login"
python3 bin/harness fleet feed
python3 bin/harness fleet claims
```

## Verification before a pull request

Run checks proportional to the change. The baseline repository checks are:

```bash
python3 lint/lint_harness.py
python3 evals/run_evals.py --dry-run
python3 cartograph/extract.py --check
```

Run every affected `test_*.py` file directly. CI additionally checks that every tracked test
is wired or explicitly excused, so adding a test without adding it to CI is a failure.

Enforcement-layer changes use `/harness-pr`: explicit approval, adversarial audit,
regression evidence, protected CI, and human merge. Ordinary product/docs changes still use
branches and pull requests, but do not need the marker cycle.

## Recovery principles

- Preserve local state before cleanup; ignored does not mean disposable.
- Do not edit generated account settings when the template is the source of truth.
- Treat guard refusals as diagnostic output first; use escape hatches only for a bounded,
  intentional recovery command.
- After a merge, return to `main` and fast-forward before starting the next branch.
- Report suspected vulnerabilities privately through [SECURITY.md](../SECURITY.md).
