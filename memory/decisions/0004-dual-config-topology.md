# ADR 0004: Dual-config topology — the harness is the account silo, not global ~/.claude

date: 2026-06-13
status: accepted
provenance: session 56295237 (fleet-silo setup) routed in 61f58113 /retro, 2026-06-13 — user verified the fleet launcher does not rewrite the silo settings.json (followup f210e7) and asked to bank the topology before it decayed. Filesystem-verified, not recalled.
corrected: 2026-06-19 (/retro-backlog, sessions 5191f317 + 43e917be) — `CLAUDE_CONFIG_DIR` points at `accounts/rhen/`, whose `hooks/` is a real symlink → the trunk.
corrected: 2026-06-24 (user, /meta-retro) — `accounts/wraith/` is NOT stale; it is a SECOND, co-active account silo (its own `settings.json` + `.claude.json`, sessions/history through 2026-06-16, same four symlinks → the trunk). The 2026-06-19 note over-declared it dead by reading "not this session's silo" as "inactive". The topology is MULTI-silo: any number of `accounts/<name>/` run concurrently, each linked to the ONE TRUNK; `rhen` is merely THIS session's silo (`CLAUDE_CONFIG_DIR`), not the only active one. (Implication: a concurrent-session guard warning on the main checkout may be a real peer silo — e.g. wraith — not a false alarm.)
extended: 2026-06-25 (session b46882f7, live under wraith) — the multi-silo model shared the BRAIN but not session HISTORY: per-account `projects/` was never shared (account-init.sh linked only the four brain dirs), so each silo's `/resume` saw only its own sessions and the stores silently diverged. User asked that `/resume` span all silos. Fix: one shared session store — see "Session store is SHARED" below. Filesystem-verified (rhen held the superset: 1322 rhen-only sessions, only 2 wraith-only).

## The topology
This Windows machine runs TWO independent Claude config homes:

1. **Account silo** `.claude-private/accounts/rhen/` — THIS session's silo (one of
   SEVERAL co-active `accounts/<name>/` silos, e.g. `rhen` + `wraith`; the topology
   applies to every per-account silo identically). Its
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

## Session store is SHARED (projects/), the brain is symlinked to the trunk
The four brain dirs (`skills/ hooks/ commands/ agents/`) symlink to the TRUNK so every
silo runs one harness. The session transcripts (`projects/`) are handled differently:
they are SHARED ACROSS SILOS so `/resume` sees every session regardless of which silo
launched it. One silo owns the real store — `accounts/rhen/projects/` ("rhen owns it",
chosen for minimal data movement: it already held the superset) — and every other silo's
`projects/` is a symlink → there. `account-init.sh` wires this for new/empty silos; a silo
whose `projects/` is already a populated real dir is left untouched with a warning and
consolidated ONCE, losslessly, by `./sync-account-sessions.sh <name>` (merge-then-cutover).

Failure modes:
- A session created under silo A will NOT appear in silo B's `/resume` unless this symlink
  is in place; without it the two stores silently diverge. The fossil
  `accounts/rhen/projects.oldlink` (→ `accounts/wraith/projects`) is the remains of an
  earlier, severed sharing attempt — `sync-account-sessions.sh` removes it on cutover.
- The cutover renames `<silo>/projects`, which Windows blocks while a session of THAT silo
  holds a transcript open. Run it with no live session of the target silo (a session of a
  different silo, or a plain terminal, is fine).

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
