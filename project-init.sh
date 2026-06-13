#!/usr/bin/env bash
# Initialize a project to CONSUME the harness without forking the brain.
# Writes a deliberately thin project CLAUDE.md. Run from the project root.
set -euo pipefail
if [ -f CLAUDE.md ]; then
  echo "CLAUDE.md already exists — appending harness contract if missing."
  grep -q "Harness contract" CLAUDE.md && { echo "already initialized"; exit 0; }
fi
cat >> CLAUDE.md << 'TPL'

## Harness contract (do not bloat this file)

This project consumes the shared harness (the fleet account's config dir, or a
legacy ~/.claude install). Rules:
- Only facts true of THIS repo belong here: build quirks, domain glossary,
  invariants. One line each. No procedures, no preferences, no wisdom —
  those route upstream (skill: routing-learnings).
- Learnings discovered here are proposed to the harness repo via /retro,
  never accumulated locally. Seen in a second project = promote upstream.
- Keep this file under 40 lines. If it grows, something is misrouted.
TPL
echo "Project initialized. Thin CLAUDE.md contract appended."
