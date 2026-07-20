# Phase 2 path-authority design

Baseline: 49 open `py/path-injection` alerts at
`19753b6c96fb124b8e6ba1e4f97b887a02bb553d`. The machine-readable inventory is
[`phase-02-baseline.json`](phase-02-baseline.json); the one-row-per-alert review is
[`phase-02-resolutions.json`](phase-02-resolutions.json).

## Trust boundaries

| Input | Authority | Policy |
| --- | --- | --- |
| Cartograph `--root` | Local operator selects one repository | Repository content is untrusted. Reads and default writes resolve inside the selected root and reject symlink escapes. |
| Cartograph explicit baseline/output path | Local operator grants one file capability | May be outside the repository by design. Repository files cannot choose or modify it. |
| Claude hook `cwd`, `session_id`, `transcript_path` | Installed host supplies an event capability | Normalize before use; owner/state data stays in the harness private-state root; final transcript and peer symlinks are refused. |
| `worktree-repos.json` path | Tracked repository data | Must be a relative child, remain inside both worktree and primary roots after realpath, and pass containment before any target probe. |
| Candidate worktree `.git` content | Untrusted repository data | May certify staleness only when its pointer resolves inside this checkout's `.git/worktrees` namespace. Any uncertainty protects the tree. |
| Eval grader sandbox argument | Eval runner-selected disposable root | The grader uses fixed filenames inside the selected sandbox; executing the candidate `rotate.py` is the explicit purpose of this test-only capability. |
| Test fixture paths | Test runner-selected temporary roots | Test-only capabilities; no production consumer imports them. |

The runtime does not claim protection from a malicious same-user process racing filesystem
operations; that process already has the harness user's permissions. It does prevent repository
content, path aliases, final symlinks, root-prefix collisions, and malformed provider fields from
silently expanding a declared capability.

## Shared rules

1. Lexical containment rejects absolute paths, cross-drive paths, parent traversal, and root-prefix
   collisions before filesystem access.
2. Realpath containment rejects symlinks and junctions that leave a declared root.
3. A final target existence check uses `lexists`, so it preserves no-clobber behavior without
   following a target symlink.
4. Private machine state is read and written through `private_state` with an explicit root.
5. Local-operator output arguments stay explicit capabilities; they are not misleadingly labeled
   vulnerabilities simply because they can name an arbitrary path.
6. Every false-positive or test-only resolution is individual. No alert is bulk-dismissed.

## Source suppression policy

CodeQL does not currently recognize this repository's `realpath` plus `commonpath` containment
helpers as taint sanitizers. A narrow `# codeql[py/path-injection]` suppression is therefore allowed
only immediately before an individually reviewed sink and only when the preceding line starts with
`CODEQL-SUPPRESS:` and states the exact authority. Suppressions are also used for the four disposable
eval-grader sinks and three test-fixture sinks already classified `used_in_tests`. The executable
contract `test_every_source_suppression_has_an_adjacent_boundary_justification` rejects anonymous
suppressions. The query remains enabled repository-wide; there is no path, suite, or query exclusion.

## Red-to-green evidence

The red commits are `b4b8d30`, `feadd38`, `2bda051`, `a6f607f`, and `4539b12`. They demonstrate, respectively,
the hook/materialization paths, a Cartograph repository symlink read, a Cartograph default-output
symlink escape, cross-platform relative-path properties, and the Windows extended-path alias race
found by the repository-wide run. `tests/test_codeql_path_boundaries.py` and
`tests/test_private_state.py` exercise the actual sinks plus deterministic path properties. The
final hosted CodeQL run and live-zero API receipt are added only after the reviewed change reaches
`main`.
