# Support

Recursive Harness is beta, maintainer-supported software. Support applies to the latest
commit of `main`; there are no long-term support branches or response-time guarantees.

## Before opening an issue

1. Read [Getting started](docs/getting-started.md),
   [Compatibility and upgrades](docs/compatibility.md), and
   [Product surface and stability](docs/product-surface.md).
2. Run `python3 bin/harness doctor` with the intended `CLAUDE_CONFIG_DIR` loaded.
3. Reproduce on a clean branch with the latest `main` and remove credentials, personal data,
   transcripts, and private repository details from the report.
4. Search existing issues, then open a GitHub issue with the observed result, expected result,
   platform/runtime versions, minimal reproduction, and relevant sanitized logs.

Supported-surface safety, data-loss, privacy, and upgrade regressions are prioritized.
Experimental/product-build artifacts are best-effort until promoted through the criteria in
the product-surface document. The global legacy installer is maintained only as a guarded
compatibility path.

## Security and sensitive reports

Do not open a public support issue for a suspected vulnerability or exposed credential. Use
the private process in [SECURITY.md](SECURITY.md). Revoke leaked credentials immediately and
sanitize every attachment.

Support classification is not a license grant. This public repository currently has no
repository-wide license; the maintainer must resolve that separately.

<!-- provenance: 2026-07-17 public-product documentation review. -->
