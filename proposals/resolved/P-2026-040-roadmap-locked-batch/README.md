---
id: P-2026-040
title: Roadmap items 2–10 — locked-path batch
status: approved
implementation: landed
created: 2026-07-05
updated: 2026-07-18
owner: GhostlyGawd
resolution: "PR #225"
---
> **Current:** `approved` decision · `landed` implementation

## Status history

| Date | Decision | Implementation | Evidence |
| --- | --- | --- | --- |
| 2026-07-17 | approved | landed | PR #225; byte-identical staged application and green verification recorded at merge |
| 2026-07-18 | approved | landed | P-2026-042 removed obsolete executable staging duplicates; PR #225 and Git history retain evidence |
<!-- proposal-history:end -->

## Resolution

PR #225 landed the approved locked-path batch: eval replay receipts, Guard A/B
eval cases, evidence-counting rules, heal autocapture, skill outcome tags,
autonomy status, and their CI wiring. The approval marker was revoked after the
verified application.

The temporary `staged/` copies were removed during P-2026-042 security cleanup.
They duplicated executable files already present in the live tree, confused
source/security scanners, and had no runtime role after landing. Their exact
pre-application content and review history remain recoverable from Git history;
the durable resolution evidence is PR #225 and the active files it merged.
