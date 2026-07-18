# Distribution — how the harness reaches a machine, an account, a project

## Identity

A virtual department: ten root-level scripts (no directory of their own) that
install, wire, and synchronize the harness. `install.sh` (installer; the
global `~/.claude` path is demoted to `--global-legacy`), `account-init.sh`
(makes a fleet account's CLAUDE_CONFIG_DIR a complete, siloed view of this
repo: real symlinks for agents/commands/hooks/skills + settings.json
materialized from templates/), `project-init.sh` (lets a foreign project
CONSUME the harness via a thin CLAUDE.md contract — never forking the brain),
`launch.sh` / `launch.ps1` (validate and visibly select one account before
starting Claude Code without changing the working directory),
`statusline-command.sh` (the fleet HUD: context % + 5h/7d rate-limit usage),
`sync-account-sessions.sh` / `.ps1` (one-time lossless cutover that consolidates
a silo's session store into the shared canonical one), and `uninstall.sh` /
`.ps1` (removes harness-owned wiring while preserving local data and user hooks).

## Why (provenance)

`install.sh` + `project-init.sh` shipped with v0.1.0 (`c72ba4a`). The fleet
silo model arrived in `ba54eba` (2026-06-13): per-account config dirs had
split from the trunk, so account-init became the documented default and the
`~/.claude` hijack was demoted behind `--global-legacy`. The HUD landed the
same day (`3f19cd6`). The session-store sharing pair came 2026-06-25:
`930b021` (one store across silos so /resume spans them, ADR 0004 "extended")
and `2d629b2` (native PowerShell variant — the bash one was unusable on a
stock Windows PowerShell).

## Contract

- **Order of operations for a new account:** external fleet tooling creates
  `.claude-private/accounts/<name>/` and pins CLAUDE_CONFIG_DIR →
  `./account-init.sh <name>` completes/repairs it idempotently. It refuses
  any target outside the silo or equal to `~/.claude` (safety gate).
- **`--sync-settings`** regenerates the live silo settings.json FROM
  `templates/account-settings.json` (backs up first) — wiring changes deploy
  through the template, never by editing a live silo file (ADR 0004).
- **Shared-store ownership:** `--store-account <name>` or
  `HARNESS_STORE_ACCOUNT` selects the canonical transcript store. The choice
  persists in ignored `.claude-private/session-store-account`; a new install
  defaults to its first account, while an existing `rhen/projects` layout is
  detected once for compatibility.
- **Launch:** `./launch.sh <account>` and `.\launch.ps1 <account>` refuse an
  uninitialized silo, print the account/config/checkout, export
  `CLAUDE_CONFIG_DIR`, forward arguments, and retain the caller's working
  directory.
- **Code vs wiring:** merged hook-code fixes go live when the trunk working
  tree updates (the silo hooks/ is a symlink); distribution scripts are only
  involved when WIRING or silo STRUCTURE changes.
- `project-init.sh` writes the thin consumer CLAUDE.md (kernel directive 6:
  project files stay thin; learnings PR upstream).
- The sync-* pair is ONE-TIME per silo (merge-then-cutover); on this Windows
  host use the `.ps1` (bash is not on a stock PowerShell PATH).

## Operations (how to extend correctly)

- None of these scripts are enforcement-locked — ordinary branch + PR — but
  they MUTATE enforcement-adjacent surfaces (settings.json wiring, symlinks),
  so changes inherit ba54eba's smoke-test contract: the out-of-silo gate
  refuses, a fresh init makes REAL symlinks, re-runs are idempotent, sync
  backs up before overwriting.
- Symlink creation on Git-Bash/MSYS requires `MSYS=winsymlinks:nativestrict`
  or `ln -s` SILENTLY COPIES and forks the brain — verify with `ls -la`
  (ADR 0004, "Maintaining the symlinks").
- The session-sync `.ps1` and its test must stay ASCII-only (Windows PowerShell
  5.1 misparses UTF-8). CI runs the test under both Windows PowerShell 5.1 and
  PowerShell 7; `tests/test_distribution.py` covers hook coexistence,
  initialization, permissions, idempotency, and both launchers.
- statusline changes come in two parts. The script itself lives here
  (unlocked) and must tolerate missing/non-numeric JSON fields (the ba54eba
  nit-fix hardened awk inputs). Its WIRING lives in
  templates/account-settings.json, which IS enforcement-locked — that half
  routes via /harness-pr and the marker cycle.

## Failure & learning

- Paid-for failures, each encoded above: config edits landing in a dead
  skeleton (pre-ba54eba); a copied "symlink" silently forking the brain
  (MSYS); silos' session stores silently diverging until /resume lost
  sessions (930b021); the bash cutover being unusable on the host it was
  written for (2d629b2); UTF-8 bytes crashing PS 5.1; custom `post-merge`
  logic being silently replaced; and a maintainer-specific shared-store name.
- The cutover REFUSES when the store isn't a complete superset — a refusal
  is the tool working, not a bug; forked same-path transcripts are backed up
  `.forked.<ts>`, never merged silently.
- Topology learnings amend ADR 0004; script bugs are heal-ledger material;
  structural changes to the silo model warrant a proposal first.

## Release archives and removal

`python3 scripts/build_release.py` packages the exact committed `HEAD` into
deterministic `.tar.gz` and `.zip` archives. Each archive includes a manifest of
the revision, file modes, sizes, and hashes; the builder also writes a SHA-256
sidecar. It refuses a dirty worktree by default so local edits cannot be mistaken
for the reviewed release.

Removal is intentionally non-destructive:

```bash
./uninstall.sh --account dev       # one silo
./uninstall.sh --all-accounts      # every local silo
./uninstall.sh --global-legacy     # only if ~/.claude links to this checkout
```

On Windows, the equivalent native entry point is
`.\uninstall.ps1 -Account dev`. The script removes repository-owned Git-hook and
account-link wiring. It does not delete the checkout, settings, overrides,
transcripts, backups, or ignored state; the operator decides when retained data
is safe to remove.

<!-- provenance: 2026-07-02, session 018UbVEr… — codification loop iteration 19
(criterion 1): virtual-department doc for the six root distribution scripts,
researched from their own headers, commits c72ba4a/ba54eba/3f19cd6/930b021/
2d629b2, and ADR 0004. Placed at root DISTRIBUTION.md because the department
has no directory (creating one = out-of-scope file moves); deviation flagged
in the wave-2 PR description. -->
