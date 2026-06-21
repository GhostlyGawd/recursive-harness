# ADR 0004: Dual-config topology — the harness is the account silo, not global ~/.claude

date: 2026-06-13
status: accepted
provenance: session 56295237 (fleet-silo setup) routed in 61f58113 /retro, 2026-06-13 — user verified the fleet launcher does not rewrite the silo settings.json (followup f210e7) and asked to bank the topology before it decayed. Filesystem-verified, not recalled.
corrected: 2026-06-19 (/retro-backlog, sessions 5191f317 + 43e917be) — the active silo is `accounts/rhen/`; this ADR previously named the stale `accounts/wraith/`. Re-verified on disk: `CLAUDE_CONFIG_DIR` points at `accounts/rhen/`, whose `hooks/` is a real symlink → the trunk.

## The topology
This Windows machine runs TWO independent Claude config homes:

1. **Account silo** `.claude-private/accounts/rhen/` — THIS harness (the active
   silo; the topology applies to any per-account silo `accounts/<name>/`). Its
   `skills/ hooks/ commands/ agents/` are real symlinks → the trunk
   `D:\GitHub Projects\recursive-harness\...`. It has its own `settings.json`
   (HUD + hooks, ~2 KB) and `.claude.json` (runtime state). The fleet launcher
   starts Claude with this as the config dir, so the session sees the trunk.
2. **Global** `~/.claude/` (`C:\Users\rhenm\.claude`) — a SEPARATE brain. Real
   dirs, NOT symlinked to the trunk; its `skills/` holds unrelated packs
   (amazon-ads-*, notion-organizer, ...). A plain `claude` launch uses this and
   never sees the harness.

## Why it matters (failure modes)
- Add/edit a skill under `~/.claude/skills/` expecting the harness to pick it up
  → it never does; you edited the wrong brain. Symptom: a new skill won't trigger
  in a fleet session though the file is clearly there.
- Harness artifacts only reach a session launched via the silo. CWD does not
  matter; the config dir does.
- The silo `settings.json` carries the HUD + hooks; a launcher that rewrote it
  would drop those on restart. Verified 2026-06-13 it does not (followup f210e7).
- Activating a merged hook FIX is a `git pull --ff-only` on the trunk, NOT
  `account-init.sh --sync-settings`: the silo `hooks/` symlink already points at the
  trunk working tree, so updating that tree deploys the code. `--sync-settings`
  regenerates only `settings.json` WIRING (matchers / which hook fires when) and does
  not touch hook code. (session cbb07617, 2026-06-21 — a PR deploy-note and an auditor
  both stated this backwards.)

## Maintaining the symlinks (MSYS gotcha — load-bearing)
The silo's four symlinks ARE the link to ONE TRUNK (prime directive 6). On
Git-Bash / MSYS, plain `ln -s` SILENTLY COPIES instead of linking unless
`MSYS=winsymlinks:nativestrict` is set (and Developer Mode / admin permits it).
A copied "symlink" forks the brain: silo edits never reach the trunk repo and
vice versa, with no error. When recreating the silo (new account / fresh
machine):
- create with `MSYS=winsymlinks:nativestrict ln -s <trunk>/<dir> <silo>/<dir>`
  or `cmd //c mklink /D <silo>\<dir> <trunk>\<dir>`, then
- VERIFY with `ls -la <silo>`: each must show as `dir -> /d/.../<dir>`
  (`lrwxrwxrwx`), NOT a plain directory. If it's a directory, it copied.

(skill `vendoring-skills` points here — it relies on this symlink to reach every account.)
