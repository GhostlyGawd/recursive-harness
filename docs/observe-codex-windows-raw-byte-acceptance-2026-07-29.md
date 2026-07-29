# Recursive Observe: Windows raw-byte Codex acceptance

This dated record supersedes the current-install portion of the 2026-07-19 Codex 0.144.6
acceptance for Recursive Observe. The earlier record remains historical evidence for receipt
contract version 1 and Guard. This record proves Observe receipt contract version 2.

## Accepted evidence

- Date: 2026-07-29
- Host: Windows with Python 3.12.10 and Git `core.autocrlf=true`
- Consumer: official `@openai/codex` package, Codex CLI 0.145.0
- Plugin interface: stable `codex plugin` CLI
- Marketplace source: `GhostlyGawd/recursive-harness`
- Immutable source and resolved snapshot:
  `ca5f79c69777ae72f2d70ea79332e3702734d457`
- Installed package: `recursive-observe@recursive-harness` 0.1.0
- Receipt contract: version 2, `sha256-raw-bytes`
- Package tree SHA-256:
  `e9c2ef040f3afe4f2959366b8fc327e8d8415eeb2f8112c889cf71ca269e16a6`
- Receipt-bound files verified: 8

Codex cloned default `main`, switched to the immutable source commit, and installed Observe
from the resulting Git marketplace. Every installed package file matched its receipt without
line-ending normalization. The package contained no hooks, app, or MCP surface. No other
Recursive plugin was installed.

## Consumer journeys

The acceptance used an isolated `CODEX_HOME`, isolated `USERPROFILE`, and a separate clean
Git repository containing seven existing provider and instruction files. Three synthetic
predictions were scored as hit, miss, and hit at confidence 0.9, 0.8, and 0.6.

```text
total: 3
scored: 3
pending: 0
hits: 2
brier: 0.27
repository writes: 0
repository tree unchanged: true
repository status unchanged: true
privacy contents printed: false
```

The privacy audit reported only aggregate metadata. It did not print prediction contents.
Observe state stayed under the isolated user profile.

## Protected state and rollback

Before and after the run, the recorder compared existence, size, and SHA-256 for the real
Codex configuration and existing Observe ledger. Both files were unchanged. The public
receipt stores only equality results; it does not store their paths, sizes, hashes, or
contents.

Uninstall removed the isolated Observe package. Marketplace removal removed the isolated
Recursive catalog. Uninstall preserved the isolated sidecar until temporary-directory cleanup.
No global plugin installation occurred.

The sanitized machine record is
[the 2026-07-29 raw-byte acceptance receipt](evidence/observe-codex-windows-raw-byte-acceptance-2026-07-29.json).
Replay with `scripts/record_observe_codex_windows_acceptance.py` and the immutable commit.
The recorder canonicalizes that commit before command use and creates its isolated workspace
under the operating system's standard temporary directory.

## Boundary

This proves a Git-backed Windows Codex 0.145.0 install and deterministic execution of
Recursive Observe. It does not prove a public marketplace listing, hosted-web persistence,
model-driven skill selection, a release artifact, a fresh Claude receipt version 2 install,
Guard, or another Recursive plugin. Human review, merge, and protected-main CI remain pending.

<!-- provenance: 2026-07-29; Observe receipt version 2 Windows acceptance. -->
