# Verify command and side-effect contract

| Command | Reads | State writes | Repository writes | External side effects |
| --- | --- | --- | --- | --- |
| `scorecard` | file paths, sizes, types | none | none | none |
| `atlas query` | file paths, sizes, types | none | none | none |
| `eval inspect` | case paths and bounded `meta.json` documents | none | none | none |
| `proposal diff` | one explicit confined target when it exists | none | diff output only; no apply | none |

All repository arguments are explicit. Directory traversal never follows `.git`, symlinks, or
junctions. Atlas query kinds are an allowlist, not expressions, shell fragments, regular
expressions, or repository-provided commands. Outputs are sorted for deterministic comparison.

The portable Atlas surface is a metadata inventory. It does not claim the convention-aware
dependency, lineage, enforcement, provenance, or blast-radius semantics of Recursive's full
Cartograph. Those remain part of the advanced reference runtime until separately extracted and
proven portable.

Eval inspection parses at most 64 KiB of each `meta.json` and reports validation categories, not
raw task, grader, source, or malformed metadata contents. It cannot certify model quality or the
behavior of a grader it did not execute.

<!-- provenance: 2026-07-20 session 019f6e76-5f8b-7633-8b19-d7cd457847fa —
P-2026-045 portable Verify package. -->
