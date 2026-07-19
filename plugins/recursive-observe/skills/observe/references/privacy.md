# Recursive Observe privacy contract

Observe records only fields supplied to its explicit CLI: a short task label, falsifiable
expectation, confidence, category, result, optional outcome note, identifier, and timestamps.
It does not collect prompts, transcripts, source files, repository configuration, or provider
chat history.

Before persistence, the package's narrow private-state layer recursively redacts common credential,
secret, email, IP-address, home-directory, and credential-bearing URL shapes. Redaction is
defense in depth; do not intentionally put sensitive data in the CLI arguments.

State is always `~/.recursive-harness/observe`, outside the active repository. The runtime
accepts no state-path argument or environment override, refuses to operate when that fixed
directory would be inside the active Git repository, and rejects links or junctions inside
the state boundary. It constrains owned
directories and files to the current user where the platform supports POSIX-style modes,
serializes concurrent writes, and atomically replaces rewrites.

Records remain until the operator explicitly purges them; there is no hidden retention
job. `privacy audit` prints aggregate counts and timestamps, never task/expectation/note
contents. `privacy purge` is a dry run unless `--apply` is present.

Uninstalling a provider package does not delete this shared provider-neutral state. Purge it
first or later with the same CLI if deletion is intended. Hosted environments may discard
their home/state volume according to the host lifecycle; Recursive does not claim persistence
where the provider does not offer it.

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 Observe-first privacy boundary. -->
