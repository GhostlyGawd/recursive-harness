# Compatibility and upgrades

## Supported baseline

| Component | Supported baseline | Verification status |
| --- | --- | --- |
| Python | CPython 3.12.x for the root harness | Ubuntu CI runs the complete stdlib suite on 3.12 |
| Git | Git 2.39 or newer | CI builds checksummed Git 2.39.0 source and runs the Git-facing distribution/operator journeys at that exact lower bound |
| Bash | Bash 5.x on Linux; current Git Bash on Windows | Shell scripts use Bash rather than portable POSIX `sh`; current environments are smoke-tested, not every 5.x minor |
| PowerShell | Windows PowerShell 5.1 and PowerShell 7.x for the native session-sync utility | Both runtimes are reproduced by the distribution suite |
| Operating system | Current GitHub-hosted Ubuntu, Windows, and macOS images | Distribution/operator journeys run continuously on all three; host filesystem and symlink policies still apply |
| Claude Code | 2.1.200 or newer | `harness doctor` reads `claude --version` and rejects an older or unreadable runtime; deterministic CI tests that gate with a local stub and never invokes a model |

The Fleet extraction scaffold has its own `requires-python >=3.8` contract. That does not
lower the root harness's Python 3.12 requirement.

The Claude Code minimum is the oldest version accepted for the `v0.1.2` operator contract,
not a claim that the repository can reproduce the external service. Release acceptance
still includes one real interactive predict → act → score → retro → reviewed-change replay.

## Dependencies

The core CLI, hooks, tests, eval runner, Fleet engine, and Cartograph are Python-standard-
library by design. Optional surfaces have separate dependencies:

- Mission Control: the reviewed `textual==8.2.8` snapshot from
  `mission_control/requirements.txt`.
- Fleet MCP adapter: the stable v1 line (`mcp>=1.28,<2`) with the reviewed
  `mcp==1.28.1` CI snapshot; Fleet's engine and CLI remain stdlib-only.
- Brand assets: committed SVG, PNG, JSON, CSS, and TypeScript files require no runtime
  dependency or build tool.

Installing an optional dependency does not make that subsystem part of the core runtime.
Both optional surfaces have their own CI job and weekly Dependabot update path.

## Upgrade procedure

### From v0.1.0

`v0.1.0` used an opt-out global `~/.claude` link. Stop Claude Code first and preserve the
checkout's ignored `state/` data. Update that same checkout to `v0.1.2`; the existing link still
points to exactly one checkout. Run the normal installer, then either keep the explicitly supported
legacy link or migrate to an isolated account:

```bash
./install.sh
./account-init.sh dev --store-account dev --sync-settings
python3 bin/harness --version
CLAUDE_CONFIG_DIR="$PWD/.claude-private/accounts/dev" python3 bin/harness doctor
./uninstall.sh --global-legacy   # only after the isolated account works
```

The removal command refuses a global link that does not point to this checkout. It preserves the
checkout, ignored state, account settings, backups, and transcripts. The tested rollback returns
the same checkout to the immutable `v0.1.0` tag; do not run the v0.1.0 installer against a different
directory without first inspecting its destructive global-link behavior.

### From a current beta checkout

1. Stop active harness sessions and preserve `.claude-private/` plus ignored `state/` data.
2. Return the checkout to `main`, fetch, and fast-forward only:

   ```bash
   git switch main
   git fetch origin
   git merge --ff-only origin/main
   ```

3. Re-run `./install.sh` to repair repository-owned Git-hook wiring.
4. Refresh generated account settings; each prior file is backed up before replacement:

   ```bash
   ./account-init.sh --all --sync-settings
   ```

5. Launch or export the intended `CLAUDE_CONFIG_DIR`, then run:

   ```bash
   python3 bin/harness --version
   python3 bin/harness doctor
   python3 lint/lint_harness.py
   python3 evals/run_evals.py --dry-run
   ```

6. Inspect warnings and the generated settings backups before resuming sensitive work.

## Rollback and removal

If an upgrade fails, stop active sessions, preserve `.claude-private/` and
`state/`, then check out the last reviewed tag and rerun `install.sh` plus account
settings synchronization. Restore a `settings.json.pre-sync.*` backup only when
the older template is incompatible. Published tags are immutable; fix forward
instead of moving a tag.

`./uninstall.sh --account <name>` (or `.\uninstall.ps1 -Account <name>` on
Windows) removes harness-managed links and Git-hook wiring without deleting
settings, overrides, transcripts, backups, state, or the checkout. This allows a
safe trial removal before the operator separately decides whether retained data
should be deleted.

Do not repair an upgrade by editing generated account `settings.json` files. Change the
canonical template or ignored per-account `overrides.json`, then regenerate.

## Compatibility failures

- A different config path in `doctor` means the wrong account brain was loaded.
- A copied account directory on Windows means native symlink creation failed; enable
  Developer Mode and rebuild only after preserving the silo.
- An old Python, Bash, Git, or Claude Code version is outside the supported baseline even if
  a single command happens to work.
- A populated independent `projects/` directory requires the lossless session-sync utility;
  never replace it with a link by hand.

<!-- provenance: 2026-07-17 productization review — roadmap item 6, compatibility. -->
