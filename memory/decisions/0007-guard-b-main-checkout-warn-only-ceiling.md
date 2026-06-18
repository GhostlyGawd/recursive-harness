# ADR 0007: Guard B main-checkout stays WARN-ONLY — no sound process-identity anchor exists

date: 2026-06-18
status: accepted
provenance: 2026-06-18, session d7de6b55 — the `ef975c` spike ("TRUE-PREVENTION via a process-identity anchor: walk the hook's process tree to the long-lived claude PID; verify a dep-free Windows process API + PID stability across compaction/resume"). Run after PR #40 shipped the interim non-blocking warning. Investigated empirically (env vars + a real ctypes process-tree walk) and against official Claude Code docs, not recalled.

## Context
Guard B blocks a second live session inside a `.claude/worktrees/<name>` tree via
the owner map. It deliberately does NOT block the MAIN checkout: a single long-lived
session churns its `session_id` (automatic compaction / wakeup / resume can mint a
new id), and the dead predecessor id's still-fresh heartbeat once self-locked the
live user out of their own trunk (the 2026-06-17 regression). Two harness-auditor
passes rejected main-checkout blocking — first an owner-map block, then a
transcript-mtime block — because no signal could tell a session's OWN churn/ghost
from a real second terminal. PR #40 shipped a NON-BLOCKING WARNING instead (a false
warning is harmless), and recorded the open question: sound blocking would need a
**stable per-terminal identity** — tracked as follow-up `ef975c`.

This ADR records the result of running that spike.

## Spike findings (what was actually tried)
1. **Hook-exposed identity (docs).** A hook receives `session_id`, `cwd`,
   `transcript_path`, `hook_event_name`, `permission_mode`, `effort`, `agent_id`.
   There is **no documented PID, TTY, or launch-id** — nothing stable-per-terminal.
2. **`CLAUDE_CODE_SESSION_ID` env var.** Documented as equal to the stdin
   `session_id` (same churning value), and not a documented hook input. Empirically
   it even DIVERGED from the live conversation's session_id this session
   (`70a46ec5…` env vs `d7de6b55…` payload, after a `/clear`) — confirming the
   identity signals are not a reliable, single, stable key.
3. **ctypes process-tree walk (dep-free; psutil unavailable).** Mechanically WORKS:
   `CreateToolhelp32Snapshot` + `Process32First/Next` found a `claude.exe` ancestor
   from a hook-like Python process. But the chain shape is environment-dependent
   (observed python→bash→bash→bash→claude.exe), a real hook's parent chain differs,
   and `CLAUDE_CODE_CHILD_SESSION=1` means subagents run as CHILD claude processes —
   so "walk up to claude.exe" is ambiguous about WHICH claude is the terminal.
4. **PID stability across the churn transitions — the decisive gap.** The claude
   PID *should* survive automatic compaction (same process), but per official docs
   `/clear` "might spawn a new process" and `--resume` "may or may not" — both
   **undocumented and unconfirmed**. Those are precisely the transitions whose
   session_id churn caused the 2026-06-17 self-lockout.

## Decision
Guard B's main checkout **stays WARN-ONLY**. Do NOT ship a main-checkout BLOCK
keyed on a process-identity anchor. The owner-map block for `.claude/worktrees/*`
is unchanged. The only behavioral change banked from this work is the warn-throttle
cooldown (auditor 6a / follow-up `10fc0b`).

Sound main-checkout blocking is **blocked on an upstream capability**: a stable,
documented, per-terminal identifier exposed to hooks (a launch id or terminal id
that is constant across compaction/clear/resume within one terminal and distinct
between concurrent terminals). Revisit if/when Claude Code exposes one.

## Why
- A safety BLOCK that can false-block a session against ITSELF reintroduces the
  exact 2026-06-17 regression the warn-only design exists to prevent. The candidate
  anchor cannot be shown stable across `/clear` and `--resume` (undocumented), so the
  block's core safety claim is unverifiable — the same defect that got the prior two
  attempts auditor-rejected, now resting on an OS-specific, version-fragile heuristic
  that "breaks if Claude Code changes how it spawns processes."
- Shipping it anyway to satisfy the literal follow-up would be reward-hacking an
  enforcement-layer change (kernel directive 5) and would fail the mandatory
  harness-auditor gate. A warning is the correct ceiling: it surfaces the collision
  without ever bricking a session.

## Alternatives rejected
- **Ship the ctypes-PID block (best-effort).** Unsound for the reason above;
  false-block risk is unverifiable and the mechanism is undocumented/fragile.
- **Use the PID anchor to make the WARNING smarter (advisory only).** Adds fragile,
  OS-specific complexity to a path that must stay fail-safe and simple, for marginal
  precision over transcript liveness. Not worth the surface area; revisit only with a
  documented signal.
- **Keep re-spiking each session.** This ADR exists so the next session does not
  redo a settled negative. The residual is an UPSTREAM ask, not a local build.
