# templates/ — canonical account config

## Identity

One payload file (plus this README): `account-settings.json` — the PORTABLE
canonical for every fleet
account's live settings.json (statusLine, permissions, all 22 hook wirings,
account defaults), with `{{REPO_ROOT}}` placeholders instead of machine paths.
`account-init.sh` materializes it into a real `<CLAUDE_CONFIG_DIR>/settings.json`
per account silo, substituting the local repo root; per-account deviations go
in `accounts/<name>/overrides.json` (gitignored), deep-merged last. The file's
own `_provenance` key states the editing rule: edit HERE, never in a live
account settings.json.

## Why (provenance)

Born `ba54eba` (2026-06-13, session 56295237): stage 1 of the fleet-config
restructure. Per-account config had split from the trunk skeleton, letting a
statusLine edit land in a dead copy that no session read. The fix: one portable
canonical inside the repo, materialized idempotently into each silo, never
touching the OS-global `~/.claude` (ADR 0004, dual-config topology).

## Contract

- **Deploy path:** `account-init.sh --sync-settings` reads THIS template and
  regenerates the live silo settings.json (backing up first). The silo's brain
  dirs (skills/ hooks/ commands/ agents/) are real symlinks to the trunk.
- **The paid-for rule** (ADR 0004; session 9f6014a0, found only at deploy time,
  scored a prediction miss): hook WIRING changes go in THIS template — a hook
  wired only in the trunk-root settings.json never reaches the live config-dir
  copy and never fires.
- **Wiring deploy ≠ code activation** (session cbb07617 — a PR deploy-note and
  an auditor both stated it backwards): a merged hook FIX goes live when the
  trunk working tree updates (the silo hooks/ symlink already points there);
  `--sync-settings` is needed only when the WIRING itself changed.
- Wiring parity: the template's 22 hook wirings mirror the trunk-root
  settings.json inventory documented row-by-row in memory/nudge-provenance.md.

## Operations (how to extend correctly)

- templates/ is enforcement-locked — it IS the deployed enforcement wiring:
  edits go via /harness-pr with the marker cycle, harness-auditor, human merge.
- To wire a new or re-matched hook: edit the template, then run
  `account-init.sh --sync-settings` per account. Never wire a hook before its
  file exists (a wired-but-missing file exits 2 on every matched tool call).
- Verify a change: the JSON parses; wiring parity against the trunk-root
  settings.json holds; account-init.sh's safety gates still refuse out-of-silo
  targets and re-runs stay idempotent (ba54eba's smoke-tested contract).

## Failure & learning

- Failure modes it exists to kill: config edits landing in a dead skeleton
  (the pre-ba54eba split) and machine paths leaking into the trunk (the
  placeholder discipline).
- Editing a LIVE silo settings.json directly creates divergence the next
  `--sync-settings` will clobber — the template is the source of truth.
- Topology learnings accrete in ADR 0004 (corrected/extended live three times:
  2026-06-19, 2026-06-24, 2026-06-25 — multi-silo, shared session store);
  wiring provenance lives per-row in memory/nudge-provenance.md.
