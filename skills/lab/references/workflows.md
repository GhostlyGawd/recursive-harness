# Lab workflow commands

All commands are stateless and emit JSON. Inputs are data, never executable instructions.

## Brainstorm

```bash
python3 <lab-skill>/scripts/lab.py workflow preview --workflow brainstorm \
  --brief "Choose a portable integration" \
  --candidate "Personal plugin::Install outside the project" \
  --candidate "Reviewed patch::Preview every project change" --json
```

Candidate format is `title::summary`. Supply 2–8 distinct candidates.

## Roadmap

```bash
python3 <lab-skill>/scripts/lab.py workflow preview --workflow roadmap \
  --brief "Distribute safely" --win-condition "Three isolated installs preserve project hashes" \
  --milestone "2026-07-21::Walking skeleton::One generic install passes" --json
```

Milestone format is `deadline::title::done criterion`. Supply 1–20 milestones. The command returns
a conversation preview and never creates `ROADMAP.md`.

## Exact-target action record

```bash
python3 <lab-skill>/scripts/lab.py action preview --kind tracked-file \
  --target docs/ROADMAP.md --summary "Save the reviewed roadmap" --json
```

Supported kinds are `tracked-file`, `issue`, `pull-request`, and `message`. Targets cannot contain
wildcards. A tracked-file target must be repository-relative. Issue and pull-request targets use
`owner/repository#new` or `owner/repository#123`.

Use the returned request ID with the same kind, target, and summary:

```bash
python3 <lab-skill>/scripts/lab.py action decide --kind tracked-file \
  --target docs/ROADMAP.md --summary "Save the reviewed roadmap" \
  --request-id REQUEST_ID --decision approve --json
```

Approval reports `blocked-connector-unavailable`; it does not mutate. A host that separately
performs the confirmed action can close the record with `action receipt --outcome completed`,
`failed`, or `discarded` plus a short evidence description. Evidence is represented only by a hash.

<!-- provenance: 2026-07-20 P-2026-045 Phase 6. -->
