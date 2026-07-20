# Verify security and privacy boundary

Verify is stateless and has no telemetry or hosted service. It does not persist repository paths,
metadata, scorecards, eval results, proposal text, prompts, or source content. Output goes only to
the invoking process's standard output and error streams.

Structural commands inspect file names, sizes, and types without reading file contents. Eval
inspection reads only bounded `meta.json` documents and emits validation status without echoing
their values. Proposal diff reads the one target explicitly selected by the user when it already
exists because an exact diff requires the prior text; the caller should treat that explicit output
as repository content.

The package does not execute repository scripts, graders, hooks, binaries, shell text, regular
expressions, model prompts, or configuration. It is not a sandbox, malware scanner, secret
scanner, full static analyzer, or proof that an application is correct. Symlinks and junctions
are reported and skipped rather than followed.

<!-- provenance: 2026-07-20 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-045 portable Verify package. -->
