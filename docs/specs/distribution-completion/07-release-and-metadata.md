# Release and repository metadata

Phase: 7

Produce and publish a reproducible v0.1.2 release whose assets, compatibility evidence,
documentation, and live repository metadata agree.

## Tasks

- [ ] Reconcile `VERSION`, changelog, README, compatibility matrix, manifests, package
  versions, migration notes, and source-install/uninstall paths.
- [ ] Build release archives twice in clean environments and require byte-identical output,
  complete SHA-256 checksums, provenance, licenses, and package receipts.
- [ ] Test fresh install, upgrade from the actual v0.1.0 tag, downgrade/rollback, and
  uninstall while preserving user data by default and disclosing destructive cleanup.
- [ ] Run the complete acceptance, security, privacy, provider, and optional Fleet/MCP
  matrices on supported systems; label macOS and unpinned providers accurately.
- [ ] Create the immutable v0.1.2 tag and GitHub Release only from the verified commit, then
  update the repository description and release/download calls to action.
- [ ] Download every published asset as a consumer and verify filename, contents, checksum,
  install, version output, and rollback.

## TDD

Start with a release-acceptance test that fails on version drift, missing changelog/assets,
non-reproducible archives, incomplete checksums, or unsupported claims. Test release scripts
against a local fixture before allowing tag/release operations.

## Property tests

Generate archive orderings, file timestamps, permissions, Unicode paths, excluded secrets,
and interrupted upgrades. Builds from the same commit must be byte-identical; archives may
not escape on extraction; failed upgrades must preserve the prior executable and user data.

## BDD scenarios

Given a new user downloads v0.1.2 from the GitHub Release
When they verify the checksum and follow the supported install path
Then the installed version and packaged receipts match the tagged source

Given a v0.1.0 user performs the documented upgrade and then rollback
When either transition completes or fails
Then their private data is preserved and exactly one supported executable state remains

## Verification gate

Phase 8 cannot advance until protected `main` is green, artifacts are reproducible, install/
upgrade/rollback/uninstall journeys pass, the live tag and release assets verify after
download, and the GitHub description and all documentation accurately say v0.1.2.

## Completion evidence

- Clean-build manifests, byte hashes, checksums, licenses, and provenance.
- Compatibility, fresh-install, upgrade, rollback, and uninstall transcripts.
- Tag-to-commit and GitHub Release API receipts.
- Post-publication download and checksum/install verification.
- Live repository description, README, changelog, and version reconciliation capture.
