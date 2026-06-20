# Recursive Harness

A self-improving harness for Claude Code, built on one premise taken seriously: **the model's weights are frozen, so the harness is the entire learnable parameter space.** Learning is defined as committing reviewed diffs to this repository — never as accumulating prose memory. Everything below follows from that definition.

This repo is the shared brain. By default it runs **siloed inside the repo**: a fleet of Claude Code accounts each runs from its own config dir under `.claude-private/accounts/<name>/` (gitignored, pinned by `CLAUDE_CONFIG_DIR`), which views the harness through symlinks plus a `settings.json` generated from a portable canonical — so the harness never writes to or touches the OS-global `~/.claude`. (A legacy single-user `~/.claude` install is still available, opt-in.) One brain, every account, versioned, shippable to GitHub, and improvable only through a pipeline that lints, audits, and regression-tests its own changes.

## Quick start

```bash
git clone <your-fork> recursive-harness && cd recursive-harness

# Fleet / siloed (default): complete a per-account config dir INSIDE the repo.
# The fleet tooling pins CLAUDE_CONFIG_DIR; this fills the dir in (symlinks + generated settings).
./account-init.sh <name>      # or, inside a fleet session: ./account-init.sh
./project-init.sh             # run in a project root for its thin CLAUDE.md contract

# Single-user global (legacy, opt-in): symlink the whole repo to ~/.claude.
./install.sh --global-legacy  # refuses if ~/.claude is a real dir or CLAUDE_CONFIG_DIR is set
```

From then on: work normally. The hooks watch, the kernel routes, `/retro` harvests.

## Add the harness to an existing repo on this machine

Two independent steps — NEITHER is auto-created:

1. **Load the brain (persistent).** In a terminal IN that repo, start Claude with
   the harness config dir pinned:
   `CLAUDE_CONFIG_DIR=<harness>/.claude-private/accounts/<name> claude`. A plain
   `claude` loads the OS-global `~/.claude`, NOT this harness (ADR 0004). The pin
   is what makes the session run this shared brain, so persist it (export it in
   that shell or your launcher) — every session in the repo needs it.
2. **(Optional) thin project contract.** Run `./project-init.sh` in the repo root
   to write a thin local `CLAUDE.md` (repo-specific facts only, < 40 lines). Skip
   it when the repo needs no project-local facts — the brain still loads from step 1.

Caution: a sibling launcher script (e.g. `fable-harness`, a `Hybrid` wrapper)
pins a DIFFERENT `CLAUDE_CONFIG_DIR` and loads a DIFFERENT brain — starting a
session through the wrong launcher silently gives you the wrong harness. If
behavior surprises you, check which config dir is actually pinned.

## The architecture in one paragraph

A 60-line kernel (`CLAUDE.md`) is the only always-loaded instruction. Six skills load on trigger and encode the system's procedures: how to route a learning, how to predict-then-score, how to detect being stuck, how to retrospect, how to author harness artifacts, how to capture regression evals. Three fresh-context agents do the jobs that must not share the working context: a critic that grades finished work, a retro-miner that reads transcripts for signal, and a harness-auditor that adversarially reviews every proposed harness diff. Six lifecycle hooks enforce mechanically what prose can only suggest. Six commands give the human and the agent named workflows. Hot telemetry lives in gitignored `state/`; durable knowledge lives in versioned `memory/`; ground truth lives in `evals/corpus/`. A linter holds the whole structure to budgets, and an autonomy ledger meters how much of the loop runs without a human.

## How each requirement is solved

**Self-improvement without weight updates.** The improvement loop is: signal → routed artifact → linted diff → adversarial audit → PR → (optionally automated) merge → regression evals. Every step is inspectable, every change reversible. The unit of learning is a diff with a `provenance:` line naming the session and event that earned it. Rules without receipts get pruned at the next `/meta-retro`.

**Verified self-awareness and judgement.** You cannot verify a feeling; you can verify a ledger. Before any non-trivial task the agent logs a falsifiable prediction (`harness predict --expect "root cause is X; ≤2 files; suite green" --confidence 0.7`) and scores it afterward. `harness stats` then shows claimed confidence against actual hit rate per bucket and per category, with Brier scores. Overconfidence is not a vibe to discuss — it is a number on a specific category, and `/calibrate` attaches a corrective rule to it. Judgement about its *own work* is structurally protected from sunk cost: the critic agent receives only the original request, the rubric, and the artifact paths — never the builder's reasoning.

**Using every tool, and improving the tools.** The `routing-learnings` skill is a strict decision tree: mechanically enforceable rule → hook; repeatable procedure → skill; user-initiated workflow → command; isolated role → agent; user taste → evidenced user-model entry; single-project fact → that project's thin CLAUDE.md; everything else → discarded. The tree's first lesson is that most "memories" people hoard are actually misfiled hooks and skills. The artifacts themselves are then subject to `/meta-retro`: fire rates are logged per skill (a PostToolUse hook), zero-fire skills become prune candidates, frequently-overridden artifacts get fixed or killed, and descriptions of under-triggering skills get rewritten to be pushier.

**Why auto-memory is structurally impossible, not just discouraged.** There is no free-prose store. The linter (`lint/lint_harness.py`) rejects user-model bullets lacking `(evidence: N, last: DATE, source: ...)`, rejects artifacts without provenance, rejects a kernel over 60 lines, rejects skill descriptions over 600 chars. The cheat doesn't fail review — it fails CI. Compression pressure doubles as quality pressure.

**No reward hacking.** The agent's cheapest path to better metrics is weakening the instruments that measure it. So the enforcement layer — `hooks/`, `lint/`, `evals/`, `autonomy.json`, `settings.json`, `.github/` — is write-locked by a PreToolUse guard that exits 2 on any mutating tool call targeting those paths inside the harness, unless a human has placed a `HUMAN_APPROVED` marker. The guard fails open on malformed input (a broken hook must never brick a session) and is scoped to this repo only. The autonomy ledger hard-codes `enforcement: graduable=false`, and the linter rejects any edit that changes that. Three layers deep: prose rule in the kernel, mechanical block in the hook, schema check in the lint.

**Autonomy, graduated rather than granted.** Every category of change (skills, commands, agents, user-model, memory) starts at zero autonomy: all changes are PRs a human reviews. `autonomy.json` tracks proposed/accepted per category; at ≥20 proposals with ≥95% acceptance, `/meta-retro` may propose flipping that category to auto-merge — itself a human-reviewed change. Trust is earned per category from measured agreement, and the measuring stick can never be auto-modified.

**Right track / wrong track, and trainable intuition.** Two mechanisms. In-flight: the logged prediction is a tripwire — the moment observed reality diverges from `--expect`, the agent stops and re-plans rather than pushing through. Across failures: the `stuck-detection` ladder (strike 1: fix the hypothesized cause; strike 2: state the broken assumption aloud and switch *strategy class*, not parameters; strike 3: escalate with falsified hypotheses in hand). Every derailment then routes somewhere permanent — a hook if the cause was mechanical, a skill if it was a knowledge gap, a user-model entry if it misread the human. Intuition improves because its failures are never free twice.

**Getting better at this specific user, any domain.** Corrections are treated as the highest-value signal in the system. A UserPromptSubmit hook pattern-matches likely corrections into a ledger automatically (false positives are cheap; `/retro` filters). At three corrections in a session, a context nudge fires; at stop time, a Stop-hook gate blocks once and demands a retro before the agent walks away from fresh signal. The user-model file accumulates only evidenced, dated, decaying claims — `/gc` retires anything unconfirmed in 90–180 days, because taste drifts. Domain-independence falls out of the routing tree: domains differ in content, but corrections, predictions, and stuck events look identical everywhere.

**One hive mind across many accounts and projects.** Every account in the fleet, and every project on the machine, runs the same brain — each account through its own siloed config dir (`account-init.sh` materializes it from the repo: symlinks + a generated `settings.json`), so isolation of credentials/sessions never costs a forked brain. Projects get a deliberately thin local CLAUDE.md (`project-init.sh` writes the contract: repo-specific facts only, under 40 lines, anything seen in a second project gets promoted upstream). Learnings flow one direction — branch and PR into this repo — so there is exactly one trunk of accumulated intelligence. On a second machine, `git clone` + `./account-init.sh <name>` (or the legacy `./install.sh --global-legacy`) restores the whole mind; teammates can fork it; CI guards it.

**Never losing context while staying lean.** Tiered by access cost. Always-loaded: the 60-line kernel plus a one-line SessionStart status banner (calibration %, unscored debt, sessions since last meta-retro) — the entire fixed tax. Trigger-loaded: skill bodies. On-demand: memory files, ADRs, archives — greppable on disk, costing nothing until read. Hot telemetry: gitignored JSONL in `state/`. Cold: `/gc` rolls state older than 30 days into versioned monthly rollups in `memory/calibration/` and decays the user model. Nothing is forgotten — it is demoted down the access hierarchy, and the linter caps every always-loaded tier. (A vector index over these files is an acceptable later add-on only as a rebuildable cache; the files stay the source of truth — see ADR 0001.)

**Learning automations from conversation.** The pipeline from "we just did something repeatable" to "it is now infrastructure" is: retro-miner spots it in the transcript → routing tree says skill/command/hook → `harness-authoring` standards shape it → lint checks it → auditor challenges it → PR ships it → `/capture-eval` pins the behavior into the regression corpus so the next harness change can't silently break it. The corpus is the system's long-term ground truth: the only artifact that can *prove* harness vN+1 beats vN rather than feeling like it.

**External state.** Hot state is machine-local JSONL with a tiny CLI (`bin/harness`: predict, outcome, stats, corrections, skill-fired, skill-stats, gc). Durable state is the repo. The boundary rule: anything worth keeping past 30 days must survive translation into a versioned, falsifiable artifact — that translation step is where junk dies.

## The three loops

1. **Inner (per task):** predict → act under hooks → score → critic if significant.
2. **Middle (per session, `/retro`):** mine corrections + misses + stuck events → ≤3 routed diffs → lint → audit → PR.
3. **Outer (monthly, `/meta-retro`):** prune zero-fire skills, fix overridden artifacts, review calibration drift, replay evals, graduate autonomy categories, keep the kernel under pressure.

## Operating cadence

After significant tasks: `/retro` (the Stop gate will insist when you forget). Every ~10 sessions: `/calibrate` then `/gc`. Monthly: `/meta-retro`. After any accepted task that recurs or was correction-born: `/capture-eval`.

## Repository map

```
CLAUDE.md          kernel (≤60 lines, lint-enforced)     settings.json   hook registration
skills/            6 trigger-loaded procedures           agents/         3 fresh-context roles
commands/          7 named workflows                     hooks/          6 lifecycle enforcers (write-locked)
bin/harness        state ledger CLI                      lint/           self-lint (budgets, falsifiability)
memory/            user-model, ADRs, rollups (versioned) state/          hot JSONL (gitignored)
evals/             regression corpus + runner            autonomy.json   graduated-autonomy ledger
templates/         portable canonical account settings   account-init.sh per-account config-dir generator
tests/             hook behavior tests                   .github/        CI: pure-Python lint + tests
.claude-private/   per-account config dirs (gitignored)  install.sh      legacy global ~/.claude install (opt-in)
```

## Honest limits

This compounds; it does not explode. Model capability is fixed, so what grows is the elimination of repeated mistakes plus accumulated procedure and taste — most of what makes a senior engineer senior, delivered asymptotically per domain. The correction detector is a heuristic (retro filters its noise). Nothing in the harness runs headless — no `claude -p`, no Agent SDK, no API key, anywhere (ADRs 0002–0003). Regression replay happens inside your interactive session: `/run-evals` spawns one fresh subagent per corpus case (the same isolation headless mode would provide, on your ordinary subscription auth), grades via each case's `check.py` or the critic agent, and writes a results ledger. CI is pure Python — lint, hook tests, corpus structure — so it can never silently depend on a Claude invocation. The cost accepted: the replay gate is procedural rather than robot-enforced, which is why `/harness-pr` demands the replay report in the body of any enforcement-layer PR. Skill fire-logging depends on the Skill tool surfacing in PostToolUse on your Claude Code version; if it doesn't, `/meta-retro` falls back to transcript grep. And the system is only as honest as its scoring — which is why unscored predictions show up in the session banner as debt, and why "unverifiable" scores as a miss.

## Provenance

Seed version 0.1.0, built 2026-06-12. Founding constraint (ADR 0001): the repo is the memory; there is no other memory.
