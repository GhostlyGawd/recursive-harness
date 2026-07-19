# Recursive Specialization for Codex

`recursive-specialization` installs only the Specialization capability. It does
not install Recursive Harness as a whole.

Version 0.1 supports local Codex hosts in the ChatGPT desktop app, CLI, and IDE.
It requires Python 3 on the host. ChatGPT web, Codex cloud, automatic prior-chat
import, and cross-device state synchronization are not supported.

## Install and trust

From a local Recursive Harness checkout, register the repository marketplace:

```text
codex plugin marketplace add <recursive-harness-checkout>
```

Alternatively register the GitHub source:

```text
codex plugin marketplace add GhostlyGawd/recursive-harness --ref main
```

Restart the ChatGPT desktop app, open **Plugins**, select **Recursive Harness**,
and install **Recursive Specialization**. Start a new chat so the bundled skill is
included in the available-skill inventory.

The plugin bundles command hooks. Codex does not run new or changed non-managed
hooks until they are reviewed and trusted. Open `/hooks`, inspect the three
Specialization lifecycle entries, and trust them. Without that trust, explicit
`$specialization` invocation still works but first-observation reminders do not.

## Migrate former local evidence

Run the exact Python executable and CLI path shown by the SessionStart hook, and
name the former checkout ledger explicitly:

```text
<cli-command-from-hook> migrate \
  --from-path "<recursive-harness-checkout>/state/skill_needs.jsonl"
```

Migration is idempotent and does not delete the former ledger.
Each open imported need without a candidate receives a private draft so it can
enter the same dogfood workflow as newly observed evidence. The importer accepts
only the documented `state/skill_needs.jsonl` shape, discards stored candidate
paths, and reconstructs private paths beneath the provider-neutral state root.

## Upgrade and rollback

Before releasing a source change, regenerate and validate the package:

```text
python scripts/build_codex_specialization_plugin.py
python scripts/build_codex_specialization_plugin.py --check
```

For Git-backed installs, refresh the marketplace with
`codex plugin marketplace upgrade recursive-harness`, then reinstall or update the
plugin from the Plugins browser and start a new chat. For local authoring, update
the plugin version/cachebuster before reinstalling so Codex replaces its cached
copy.

Rollback by selecting an earlier marketplace ref or checkout commit, refreshing
the marketplace, and reinstalling. The provider-neutral ledger remains outside
the plugin cache, so upgrade and rollback do not erase evidence.

## Remove and purge

Open the plugin in a supported Plugins browser and choose **Uninstall plugin**.
Uninstalling stops the skill and hooks but deliberately retains the private ledger
and candidates. Purging that directory is a separate destructive action; inspect
and back it up before deleting it.

## Lifecycle limitations

- The adapter cannot enumerate prior chats. It begins deterministic recurrence
  tracking after installation or explicit ledger migration.
- Hooks remind the model to make the semantic gap judgment; command hooks do not
  independently understand domains.
- Plan Mode receives advisory context only and does not write candidates.
- Provider hooks fail open if Python, input, or local state is unavailable.
- A validated candidate stays local until the user approves a canonical change.

provenance: 2026-07-18, install/upgrade/removal and unsupported-event receipt for
the first OpenAI/Codex Specialization adapter.
