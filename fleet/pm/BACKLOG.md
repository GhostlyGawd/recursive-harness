# Agent Mail — Backlog

Prioritized idea/feature candidates beyond the committed `ROADMAP.md`. Promote a card to the
roadmap when it's pulled by real use. _(Seeded by the Product lens 2026-06-30; UX lens may add.)_

## P0 — high-value, near-term
- **B-01** Session-end reaper **hook** (gated) so the on-disk log self-compacts without manual `fleet reap`.
- **B-02** `/standup` + `/retro` gain a "fleet" line (live claims / pending postbox) for discoverability.
- **B-03** Per-view TTL defaults (ambient feed ~15m vs directed handoff longer-lived) as named constants.
- **B-04** Handle-namespace normalization (`role/` vs `unit/` vs `topic/` prefixes) so addressing is unambiguous.

## P1 — valuable, not yet pulled
- **B-05** Threading: `reply_to` / conversation id on handoffs for back-and-forth without free-prose.
- **B-06** Search/filter over live events — `harness fleet feed --kind --target`.
- **B-07** Presence/heartbeat: a "who's live now" projection folded from recent actor tokens.
- **B-08** Read-only **web dashboard** over the feed (mirrors Mission Control for non-terminal contexts).
- **B-09** Multi-machine transport: a `StoreProvider` injection (shared git/S3/sqlite) so the jsonl
  syncs across hosts — the engine already takes an injected `state_dir`.

## P2 — later / speculative
- **B-10** TS/JS SDK + npm packaging (parallel to the pip path) for non-Python agents.
- **B-11** Auth/encryption for multi-tenant or untrusted-peer fleets.
- **B-12** Metrics: emit rates, claim-contention stats, postbox delivery latency.
- **B-13** Replay / time-travel debugger over the append log.
- **B-14** Per-view Mission Control panels (claims board, postbox inbox) beyond the live ticker.
- **B-15** Per-kind sub-cap in `reap` so a chatty stream can't evict unread handoffs (RISK-1).

## UX/DX (from the UX lens 2026-06-30 — most land in R5; render.py starts in the CLI step)
- **UX-P0** `fleet/render.py` (UNLOCKED): scannable feed — relative age + TTL, fixed-width columns,
  `k=v` payloads (not raw dict repr), color on tty (`NO_COLOR`-aware), `--group kind|target|actor`,
  header with counts, actor-hex hidden behind `-v`. Locked side = one-time swap to
  `for l in render.format_feed(...): print(l)`. Mission Control gets relative age + directed-handoff
  emphasis (`→handle ◀ directed`) + "+N more" footer (unlocked).
- **UX-P1** Emit ergonomics: `--set k=v` (repeatable) + `--note "…"` sugar; `--payload JSON` escape
  hatch; per-value length cap (ADR 0001). `release --target PATH` (via `release_target`).
- **UX-P2** Discoverability: bare `fleet` overview (live counts · unread postbox · active claims ·
  4-line cheat sheet) from `fleet/overview.py`; argparse `epilog=` examples; `KINDS` glossary constant.
- **UX-P3** Postbox CLI: `send HANDLE --re UNIT "msg"` · `inbox --as HANDLE` · `ack ID` (R3 surface).
- **UX-P4** Awareness (LOCKED, ships dark): SessionStart banner mirroring `heal_banner` — shown only
  when >0, count-not-content, SOFT flag `observability.fleet_banner` default OFF (via `/harness-pr`).
  Mission Control chrome `POST n · CLAIMS n` (unlocked).
