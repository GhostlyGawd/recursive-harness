# ADR 0002: All Claude execution runs on subscription CLI auth — no API keys

date: 2026-06-12
status: accepted
provenance: user correction, session 2026-06-12 ("This thing cannot use an
api key. It has to be able to do it in cli")

## Decision
Every place the harness invokes Claude (local eval replay, CI regression
evals, any future automation) authenticates through the `claude` CLI's own
subscription auth: interactive `claude login` locally, and a long-lived
`claude setup-token` OAuth token (CLAUDE_CODE_OAUTH_TOKEN secret) in CI.
ANTHROPIC_API_KEY must never be set in harness environments.

## Why
1. The operator runs Claude Code on a subscription plan; API keys are a
   separate billing surface they do not use.
2. Precedence hazard: if ANTHROPIC_API_KEY is set alongside subscription
   credentials, the key wins and can silently break auth. Banning it removes
   the whole failure class.
3. setup-token is Anthropic's supported path for headless/CI subscription
   use (one-year token, inference-scoped).

## Notes
- From 2026-06-15, `claude -p` on subscription plans draws from a monthly
  Agent SDK credit separate from interactive limits — eval replay frequency
  should respect that budget (prefer `--subset` smoke runs; full corpus on
  enforcement-layer changes).
- If a future component genuinely cannot use CLI auth, that is a design
  smell: wrap it in `claude -p` or drop it.
