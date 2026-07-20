# Learn privacy contract

Learn persists only user-supplied correction, follow-up, and candidate summaries plus timestamps,
stable identifiers, session labels, and lifecycle status. Common credentials, email addresses,
IP addresses, user-home paths, and authenticated URL values are redacted before persistence.

The only state directory is `~/.recursive-harness/learn`. The CLI has no `--state-dir` option and
does not honor an environment variable for changing that location. It refuses a location inside
the active Git repository and rejects symlink or junction traversal at the capability boundary.
Files are created with owner-only permissions where the operating system supports them.

`privacy audit` reports only paths, record counts, and the declared repository-write set. It does
not echo captured text. `privacy retain` defaults to a 30-day window and scrubs expired raw text
while preserving evidence metadata. Invalid timestamps are reported and kept for explicit review.
Both retention and full `privacy purge` are dry runs unless `--apply` is explicitly present.

Learn does not capture prompts, transcripts, model traffic, tool results, source files, Git
history, or repository configuration automatically. It provides no hosted synchronization,
telemetry, sandbox, or encryption-at-rest layer beyond operating-system account permissions.

<!-- provenance: 2026-07-19 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-044 portable Learn package. -->
