# Getting started

## Prerequisites

- Git 2.39.0 or newer
- Python 3.12, matching the CI runtime
- Bash for `install.sh`, `account-init.sh`, and the deprecated `project-init.sh` wrapper
- Claude Code 2.1.200 or newer

On Windows, use Git Bash for the shell scripts. Enable Windows Developer Mode so
`account-init.sh` can create native symlinks; the script intentionally fails instead of
silently copying the harness directories. Use the PowerShell session-sync helper when a
later migration requires it.

## Choose a source

For a versioned install, download the checksummed bundle from the
[latest GitHub Release](https://github.com/GhostlyGawd/recursive-harness/releases/latest):

```bash
gh release download v0.1.2 -R GhostlyGawd/recursive-harness \
  -p "recursive-harness-v0.1.2.tar.gz" \
  -p "recursive-harness-v0.1.2.zip" \
  -p "recursive-harness-v0.1.2.sha256"
sha256sum -c recursive-harness-v0.1.2.sha256
tar -xzf recursive-harness-v0.1.2.tar.gz
cd recursive-harness-v0.1.2
```

The sidecar verifies both downloaded archives. On macOS replace `sha256sum` with
`shasum -a 256`; on Windows compare `Get-FileHash -Algorithm SHA256` for each archive with
its sidecar line. To follow current development instead, clone
`https://github.com/GhostlyGawd/recursive-harness.git` and continue below.

## 1. Initialize the checkout

```bash
# Skip these two lines when you already extracted a release bundle.
git clone https://github.com/GhostlyGawd/recursive-harness.git
cd recursive-harness
./install.sh
```

The default installer does not change `~/.claude`. It installs a managed `post-merge`
dispatcher, prints the siloed setup path, and runs the harness linter. The harness-owned
task re-materializes account settings after the canonical template changes. If a custom
`post-merge` hook already exists, the installer preserves it byte-for-byte in
`post-merge.d/10-existing-post-merge`; both hooks then run in lexical order. A conflicting
or non-regular hook is refused for manual reconciliation rather than overwritten.

## 2. Create an account silo

```bash
./account-init.sh dev --store-account dev
```

This creates `.claude-private/accounts/dev/`, links `agents/`, `commands/`, `hooks/`, and
`skills/` back to the checkout, and materializes a machine-specific `settings.json` from
`templates/account-settings.json`. The whole `.claude-private/` tree is gitignored.

Account initialization is idempotent. To refresh live settings after a template change:

```bash
./account-init.sh dev --sync-settings
```

The existing settings file is backed up before replacement, and optional
`overrides.json` values are merged last.

The first initialized account becomes the shared session-store owner unless you select one
with `--store-account <name>` or `HARNESS_STORE_ACCOUNT`. The choice is persisted in the
ignored, owner-only `.claude-private/session-store-account` file so later accounts and Git
hooks use the same store. Existing installations with a populated `rhen/projects` store are
detected once for backward-compatible migration.

## 3. Pin the account and verify it

On Bash:

```bash
export CLAUDE_CONFIG_DIR="$PWD/.claude-private/accounts/dev"
python3 bin/harness doctor
./launch.sh dev
```

On PowerShell, after running account initialization from Git Bash:

```powershell
$env:CLAUDE_CONFIG_DIR = (Resolve-Path .\.claude-private\accounts\dev).Path
python .\bin\harness doctor
.\launch.ps1 dev
```

`doctor` verifies the loaded config directory, hook parity, Python compilation, Claude Code
minimum, ledger writability, branch position, and recent eval replay. A different pinned
config directory means a different brain; fix the launcher rather than editing the generated
account files.

The launchers validate that the account has settings, export `CLAUDE_CONFIG_DIR`, print the
selected account/config/checkout to stderr, forward Claude Code arguments, and preserve the
current working directory. A plain `claude` invocation without the pin uses the operating
system's default Claude config.

## 4. Inspect or use another repository

Start with a zero-write compatibility inspection. It checks only whether known instruction,
provider, agent, skill, hook, and GitHub configuration paths exist; it does not read or print
their contents.

```bash
python3 /path/to/recursive-harness/scripts/recursive_inspect.py /path/to/target-project
# Add --json for deterministic machine-readable output.
```

Existing `AGENTS.md`, `CLAUDE.md`, provider settings, agents, skills, and hooks remain
authoritative. The command performs no repository writes. `project-init.sh` remains only as
a deprecated wrapper for this inspection and no longer changes `CLAUDE.md`.

You can call explicit sidecar commands from the Recursive checkout while another project is
your working context. If you instead invoke `launch.sh dev` or `launch.ps1 dev`, you are
choosing the full Claude reference runtime: it preserves the target working directory but
selects Recursive's dedicated `CLAUDE_CONFIG_DIR`. That is useful isolation, not a merge
with your normal Claude setup.

Namespaced provider plugins are planned from the canonical
[capability catalog](../capabilities/README.md). Until a package has a source-hash receipt,
coexistence fixtures, and a real consumer validation, its manifest is a design contract—not
an installable compatibility claim.

## 5. Verify the working loop

```bash
python3 bin/harness predict \
  --task "verify the install" \
  --expect "doctor exits cleanly and the scorecard shows one pending prediction" \
  --confidence 0.9

python3 bin/harness doctor
python3 bin/harness scorecard
```

When the result is known, score the identifier printed by `predict`:

```bash
python3 bin/harness outcome PREDICTION_ID --result hit --notes "install verified"
```

## Optional legacy global install

```bash
./install.sh --global-legacy
```

This symlinks the checkout to `~/.claude`. It refuses to run when
`CLAUDE_CONFIG_DIR` is set or when `~/.claude` is a real directory. The siloed account
model is the supported default because it makes the loaded configuration explicit and
keeps account state inside the ignored checkout boundary.

## Upgrade, rollback, and uninstall

Use the fast-forward and settings-backup procedure in
[Compatibility and upgrades](compatibility.md). Rollback means returning the
checkout to a previously reviewed tag and restoring a generated settings backup;
never move a published tag or discard ignored state to force the downgrade.

To remove harness wiring while keeping recoverable local data:

```bash
./uninstall.sh --account dev
```

On Windows, run `.\uninstall.ps1 -Account dev`. Both entry points preserve the
checkout, settings, overrides, transcripts, backups, and `state/`. Inspect and
remove retained data separately only after confirming it is no longer needed.

## Common setup failures

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| `doctor` reports a different brain | Launcher pinned another `CLAUDE_CONFIG_DIR` | Fix the launcher or export the intended account path |
| Installer refuses an existing hook | The hook is a symlink/non-file, or a preserved copy conflicts | Reconcile the reported hook paths manually, then rerun `install.sh` |
| Account links are directories instead of symlinks on Windows | Git Bash copied because native symlinks were unavailable | Enable Developer Mode, remove only the incorrect account silo after backing it up, then rerun initialization |
| `projects/` is a populated real directory | Sessions diverged before the shared store was linked | Stop live sessions and use `sync-account-sessions.ps1` on Windows or `.sh` on Unix; the sync scripts back up conflicts |
| Settings do not match the template | Account predates a wiring change | Run `./account-init.sh dev --sync-settings` |
| A project behaves as if the harness is absent | The account pin was not present for that launch | Start Claude Code again with `CLAUDE_CONFIG_DIR` set |

Read [Privacy and local data](../PRIVACY.md) before using the setup with sensitive work.
