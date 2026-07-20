# Coordinate security and privacy boundary

Coordinate stores sanitized claim targets, short owner/handle labels, bounded topics/messages, and
lease metadata under a user-private state root. It does not store repository paths, source files,
prompts, transcripts, provider credentials, or environment dumps. Repository configuration and
content are never written.

The package makes no network request and asks for no credential. “Agent Mail” here means the local
handoff projection; it is not a claim of compatibility with a hosted Agent Mail service. The
optional Fleet MCP adapter and full Textual Mission Control in Recursive's advanced reference
runtime are not included. Connecting a future service requires a separate install, explicit
endpoint/credential choice, threat review, and consumer receipt.

The claim ledger is cooperative advisory coordination. It cannot stop a process that ignores it,
cannot provide distributed consensus, and cannot make a shared filesystem or untrusted process
safe. State-root confinement rejects repository-local roots and symlink/junction escapes. Treat
any deliberately shared private-state directory as sensitive operational metadata.

<!-- provenance: 2026-07-20 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-045 portable Coordinate package. -->
