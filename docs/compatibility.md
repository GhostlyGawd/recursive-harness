# Compatibility and upgrades

## Supported baseline

| Component | Supported baseline | Verification status |
| --- | --- | --- |
| Python | CPython 3.12.x for the root harness | Ubuntu CI runs the complete stdlib suite on 3.12 |
| Git | Git 2.39 or newer | This is the selected lower bound; a dedicated minimum-version CI job is still a release-readiness gap |
| Bash | Bash 5.x on Linux; current Git Bash on Windows | Shell scripts use Bash rather than portable POSIX `sh`; current environments are smoke-tested, not every 5.x minor |
| PowerShell | Windows PowerShell 5.1 and PowerShell 7.x for the native session-sync utility | Both runtimes are reproduced by the distribution suite |
| Operating system | Current Ubuntu LTS and current supported Windows desktop/server | macOS is best-effort until it has a continuous test job |
| Claude Code | Current stable Claude Code with settings-driven hooks and commands | No numeric minimum is guaranteed yet; `harness doctor` is the compatibility gate |

The Fleet extraction scaffold has its own `requires-python >=3.8` contract. That does not
lower the root harness's Python 3.12 requirement.

## Dependencies

The core CLI, hooks, tests, eval runner, Fleet engine, and Cartograph are Python-standard-
library by design. Optional surfaces have separate dependencies:

- Mission Control: `textual>=0.60` from `mission_control/requirements.txt`.
- Fleet MCP adapter: `mcp>=1.0`; Fleet's engine and CLI remain stdlib-only.
- Brand assets: committed SVG, PNG, JSON, CSS, and TypeScript files require no runtime
  dependency or build tool.

Installing an optional dependency does not make that subsystem part of the core runtime.

## Upgrade procedure

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
   python3 bin/harness doctor
   python3 lint/lint_harness.py
   python3 evals/run_evals.py --dry-run
   ```

6. Inspect warnings and the generated settings backups before resuming sensitive work.

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
