# ADR 0008: Feature-flag config (features.json + state/features.local.json) — convenience layer that cannot weaken enforcement

date: 2026-06-18
status: accepted
provenance: 2026-06-18, session 44bdfc6f — user asked for "a config file for this repo where I can control different features so I can easily disable or enable them to test things out," after a discussion of whether the worktree guards (A/B) carry their weight. Scope (all hook-driven features) and the safety stance ("hard blocks stay human-gated; the agent can't switch its own guards off") chosen by the user this session.

## Context
The harness has ~9 behavior-producing hooks (two worktree guards, the enforcement
guard, two Stop-gate nudges, correction/skill logging, the session banner, the
post-merge return-to-trunk reminder). The user wanted one place to flip these on/off
to experiment — but most of them live in `hooks/`, which is write-locked by
`guard_enforcement_layer.py` (kernel directive 5) precisely so checks cannot be
quietly switched off. A naive "flags file that disables guards" is the exact
reward-hacking pattern that lock exists to prevent: it would let the agent take the
cheapest path to "better metrics" by turning off the checks that produce them.

## Decision
Ship a **two-tier** config read by a shared `hooks/harness_features.py`:

- **SOFT keys** (nudges, the non-blocking concurrent-session warning + its cooldown,
  banner verbosity, correction/skill logging, post-merge reminder, follow-up TTL,
  retro cadence threshold): resolved `state/features.local.json` (gitignored) over
  `features.json` (committed) over the caller's hard-coded default. Freely flippable
  by the user OR the agent. No enforcement impact.
- **LOCKED keys** — anything that weakens a safety guard: `guards.*.block`,
  `guards.worktree_isolation.bash_scanner` (strict|lenient), and
  `guards.worktree_session.ttl_seconds`: read ONLY from the committed `features.json`,
  which is added to the enforcement guard's PROTECTED set. The local override file is
  IGNORED for these keys. So the off-switch for a hard block is human-gated two ways
  (edit the protected committed file — tracked in git, agent-blocked; or the existing
  env hatch), and the agent has no file it can write that disables a guard.

`features.json` is added to `guard_enforcement_layer.PROTECTED`. The reader fails
safe: any missing/corrupt file or bad value yields the caller's default, so a broken
or absent config behaves exactly like today. Defaults equal current behavior, so the
PR is a no-op until someone flips a flag.

## Why this is not enforcement-weakening
- An agent cannot disable a guard through the config: LOCKED keys are sourced only
  from the PROTECTED committed file (agent edits blocked by the same guard that
  protects hooks/), and the gitignored file it CAN write is ignored for those keys.
- This is not a new bypass of the blocks. Guard A/B already ship human-gated env
  hatches (`HARNESS_ALLOW_CROSS_WORKTREE` / `HARNESS_ALLOW_MULTI_SESSION`). The
  committed LOCKED flag is a second human-gated path, not a lower bar.
- Making `ttl_seconds` tunable is explicitly sanctioned by the original Guard B code
  comment ("If a tunable TTL is ever genuinely needed, add it as a human-gated config
  via /harness-pr, not an env var any session can set"). Reading it from the PROTECTED
  committed file preserves the property that motivated the fixed constant: a second
  live session cannot self-assert a tiny TTL to evict the real owner.
- The enforcement guard itself has NO flag — it is never disableable via config.

## Alternatives rejected
- **One flat gitignored flags file controlling everything, guards included.** The
  user's own choice rejected this: it reopens the agent self-disable path. (Offered as
  the "freely toggleable" option; declined in favor of "human-gated".)
- **Env-vars only, no file.** The user explicitly wanted a file they can edit; env
  vars are not discoverable and don't persist across a terminal cleanly.
- **A WorktreeCreate-style separate config service.** Over-built for a single-user
  harness; a 130-line reader + one committed JSON is the whole need.

## Surfacing
`harness features` prints the effective config (value + source: default/local/locked);
`harness features set <key> <value>` writes a SOFT override (and refuses LOCKED keys,
pointing at features.json). The SessionStart banner appends a one-line "features:
N override(s) active" note whenever the local file diverges from defaults, so a flipped
flag is never silently forgotten.
