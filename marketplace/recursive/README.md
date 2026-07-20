# Recursive public plugin submission

This directory is the durable, non-secret input for the official OpenAI public plugin
submission. It does not claim that Recursive is already listed.

Build the final ZIP from the immutable v0.1.2 release commit:

```bash
python3 scripts/build_public_plugin.py --output-dir dist/public-plugin
python3 tests/test_public_plugin_submission.py
```

The builder verifies each provider package's canonical-source receipt before copying the four
skills, writes a deterministic skills-only archive, and emits an external hash/receipt. Never
add portal credentials, organization identifiers, reviewer secrets, unpublished URLs, or
screenshots containing account data here.

The owner must still select availability, verify the publisher identity and Apps Management
permission in the portal, review policy attestations, and authorize the final submission.
