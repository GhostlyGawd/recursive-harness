#!/usr/bin/env python3
"""Black-box coexistence, enforcement, and package tests for Recursive Guard."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "skills" / "guard" / "scripts" / "guard_hook.py"
PLUGIN = ROOT / "plugins" / "recursive-guard"
BUILDER = ROOT / "scripts" / "build_guard_plugin.py"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"


def write(root: Path, relative: str, value: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def repository(root: Path, files: dict[str, str] | None = None) -> Path:
    (root / ".git").mkdir(parents=True)
    for relative, value in (files or {}).items():
        write(root, relative, value)
    return root


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def invoke(hook: Path, cwd: Path, tool: str, tool_input: dict[str, object]) -> subprocess.CompletedProcess[str]:
    payload = {
        "hook_event_name": "PreToolUse",
        "cwd": str(cwd),
        "tool_name": tool,
        "tool_input": tool_input,
    }
    return subprocess.run(
        [sys.executable, str(hook)],
        cwd=cwd,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def invoke_raw(hook: Path, cwd: Path, payload: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(hook)],
        cwd=cwd,
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def policy(root: Path, mode: str = "enforce", paths: list[str] | None = None) -> None:
    write(root, ".recursive-guard.json", json.dumps({
        "schema_version": 1,
        "mode": mode,
        "protected_paths": paths or ["AGENTS.md", ".codex"],
    }))


def decision(result: subprocess.CompletedProcess[str]) -> dict[str, object] | None:
    return json.loads(result.stdout) if result.stdout.strip() else None


class GuardBehaviorTests(unittest.TestCase):
    def test_no_policy_is_exact_noop_for_claude_and_codex_configs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory), {
                "AGENTS.md": "existing codex instructions\n",
                "CLAUDE.md": "existing claude instructions\n",
                ".codex/config.toml": "model = 'existing'\n",
                ".claude/settings.json": '{"existing":true}\n',
                ".claude/agents/reviewer.md": "existing reviewer\n",
                ".agents/skills/existing/SKILL.md": "existing skill\n",
            })
            before = snapshot(root)
            result = invoke(HOOK, root, "apply_patch", {
                "command": "*** Begin Patch\n*** Update File: AGENTS.md\n@@\n-old\n+new\n*** End Patch\n"
            })
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
            self.assertEqual(snapshot(root), before)

    def test_no_policy_is_exact_noop_for_other_agent_configs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory), {
                ".github/copilot-instructions.md": "existing copilot rules\n",
                ".cursor/rules/project.mdc": "existing cursor rules\n",
                ".windsurfrules": "existing windsurf rules\n",
                ".agents/skills/team/SKILL.md": "existing portable skill\n",
                "src/app.py": "print('unchanged')\n",
            })
            before = snapshot(root)
            result = invoke(HOOK, root, "Bash", {"command": "rm AGENTS.md"})
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(snapshot(root), before)
            self.assertEqual(invoke_raw(HOOK, root, "{malformed").stdout, "")

    def test_enforce_returns_current_codex_deny_shape_for_apply_patch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory), {"AGENTS.md": "preserve\n"})
            policy(root)
            result = invoke(HOOK, root, "apply_patch", {
                "command": "*** Begin Patch\n*** Delete File: AGENTS.md\n*** End Patch\n"
            })
            output = decision(result)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(output, {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "Recursive Guard protects 'AGENTS.md' under the repository's reviewed policy."
                    ),
                }
            })

    def test_enforce_blocks_file_alias_and_shell_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory), {".codex/config.toml": "existing\n"})
            policy(root)
            file_result = invoke(HOOK, root, "apply_patch", {
                "file_path": str(root / ".codex" / "config.toml")
            })
            shell_result = invoke(HOOK, root, "Bash", {
                "command": "Remove-Item .codex/config.toml"
            })
            for result in (file_result, shell_result):
                self.assertEqual(
                    decision(result)["hookSpecificOutput"]["permissionDecision"], "deny"
                )

    def test_enforce_blocks_move_destination_and_interpreter_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory), {
                "AGENTS.md": "preserve\n",
                "src/source.md": "move me\n",
            })
            policy(root)
            moved = invoke(HOOK, root, "apply_patch", {
                "command": (
                    "*** Begin Patch\n*** Update File: src/source.md\n"
                    "*** Move to: AGENTS.md\n@@\n-old\n+new\n*** End Patch\n"
                )
            })
            interpreted = invoke(HOOK, root, "Bash", {
                "command": "python -c \"open('AGENTS.md','w').write('x')\""
            })
            for result in (moved, interpreted):
                self.assertEqual(
                    decision(result)["hookSpecificOutput"]["permissionDecision"], "deny"
                )

    def test_unrelated_and_read_only_operations_are_silent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory), {
                "AGENTS.md": "preserve\n",
                "src/app.py": "print('ok')\n",
            })
            policy(root)
            results = [
                invoke(HOOK, root, "apply_patch", {
                    "command": "*** Begin Patch\n*** Update File: src/app.py\n@@\n-old\n+new\n*** End Patch\n"
                }),
                invoke(HOOK, root, "Bash", {"command": "Get-Content AGENTS.md"}),
                invoke(HOOK, root, "Read", {"file_path": str(root / "AGENTS.md")}),
            ]
            self.assertTrue(all(result.stdout == "" for result in results))

    def test_audit_warns_without_denying(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory), {"AGENTS.md": "preserve\n"})
            policy(root, mode="audit")
            output = decision(invoke(HOOK, root, "Bash", {"command": "rm AGENTS.md"}))
            self.assertIn("AUDIT ONLY", output["systemMessage"])
            self.assertNotIn("hookSpecificOutput", output)

    def test_policy_protects_itself(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory))
            policy(root, paths=["AGENTS.md"])
            result = invoke(HOOK, root, "apply_patch", {
                "command": "*** Begin Patch\n*** Delete File: .recursive-guard.json\n*** End Patch\n"
            })
            self.assertEqual(
                decision(result)["hookSpecificOutput"]["permissionDecision"], "deny"
            )

    def test_invalid_policy_fails_closed_for_matched_tool(self) -> None:
        invalid_values = [
            "{not-json",
            json.dumps({"schema_version": 1, "mode": "enforce", "protected_paths": ["../outside"]}),
            json.dumps({"schema_version": 1, "mode": "enforce", "protected_paths": ["a/../AGENTS.md"]}),
            json.dumps({"schema_version": True, "mode": "enforce", "protected_paths": ["AGENTS.md"]}),
            '{"schema_version":1,"schema_version":1,"mode":"enforce","protected_paths":["AGENTS.md"]}',
            json.dumps({
                "schema_version": 1,
                "mode": "enforce",
                "protected_paths": ["AGENTS.md"],
                "surprise": True,
            }),
        ]
        for value in invalid_values:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = repository(Path(directory))
                write(root, ".recursive-guard.json", value)
                output = decision(invoke(HOOK, root, "Bash", {"command": "echo safe"}))
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertIn("policy is invalid", output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_active_policy_handles_uninspectable_input_by_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory))
            policy(root, mode="enforce")
            malformed = decision(invoke_raw(HOOK, root, "{malformed"))
            oversized = decision(invoke_raw(HOOK, root, " " * (1048576 + 1)))
            for output in (malformed, oversized):
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertIn("could not inspect", output["hookSpecificOutput"]["permissionDecisionReason"])

        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory))
            policy(root, mode="audit")
            malformed = decision(invoke_raw(HOOK, root, "{malformed"))
            self.assertIn("AUDIT ONLY", malformed["systemMessage"])

    def test_oversized_command_is_not_an_enforcement_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory))
            policy(root, mode="enforce")
            output = decision(invoke(HOOK, root, "Bash", {
                "command": "echo x " + ("x" * 524289)
            }))
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_linked_policy_fails_closed_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = repository(Path(directory))
            target = root / "policy-target.json"
            target.write_text('{"schema_version":1,"mode":"audit","protected_paths":["AGENTS.md"]}')
            try:
                (root / ".recursive-guard.json").symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            output = decision(invoke(HOOK, root, "Bash", {"command": "echo safe"}))
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")


class GuardPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(BUILDER), "--check"], check=True)

    def test_receipt_binds_complete_package_and_hook_contract(self) -> None:
        receipt = json.loads((PLUGIN / "canonical-source.json").read_text(encoding="utf-8"))
        packaged = set(receipt["package_files"])
        self.assertIn("LICENSE", packaged)
        self.assertIn("hooks/hooks.json", packaged)
        self.assertIn(".codex-plugin/plugin.json", packaged)
        self.assertIn("skills/guard/scripts/guard_hook.py", packaged)
        manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertNotIn("hooks", manifest)
        hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(hooks["hooks"]["PreToolUse"][0]["matcher"], "Bash|apply_patch|Edit|Write")

    def test_copied_package_executes_without_repository_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            copied = base / "installed" / "recursive-guard"
            shutil.copytree(PLUGIN, copied)
            root = repository(base / "consumer", {
                "AGENTS.md": "existing\n",
                ".codex/config.toml": "existing = true\n",
            })
            before = snapshot(root)
            result = invoke(copied / "skills/guard/scripts/guard_hook.py", root, "Bash", {
                "command": "rm AGENTS.md"
            })
            self.assertEqual(result.stdout, "")
            self.assertEqual(snapshot(root), before)

    def test_copied_package_tamper_and_unexpected_payload_fail_receipt_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "recursive-guard"
            shutil.copytree(PLUGIN, copied)
            manifest = copied / ".codex-plugin/plugin.json"
            manifest.write_text(manifest.read_text(encoding="utf-8") + " ", encoding="utf-8")
            tamper = subprocess.run(
                [sys.executable, str(BUILDER), "--check", "--plugin-dir", str(copied)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(tamper.returncode, 1)
            self.assertIn("drift: plugins/recursive-guard/.codex-plugin/plugin.json", tamper.stderr)
            self.assertNotIn("Traceback", tamper.stderr)

        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "recursive-guard"
            shutil.copytree(PLUGIN, copied)
            write(copied, "unexpected.txt", "not receipt-bound\n")
            unexpected = subprocess.run(
                [sys.executable, str(BUILDER), "--check", "--plugin-dir", str(copied)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(unexpected.returncode, 1)
            self.assertIn("unexpected packaged file: unexpected.txt", unexpected.stderr)

    def test_marketplace_keeps_guard_separate_from_advisory_plugins(self) -> None:
        marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        names = [entry["name"] for entry in marketplace["plugins"]]
        self.assertEqual(names, [
            "recursive-observe", "recursive-specialization", "recursive-guard"
        ])
        for entry in marketplace["plugins"]:
            self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
            self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
        for plugin in (ROOT / "plugins").iterdir():
            manifest_path = plugin / ".codex-plugin/plugin.json"
            if plugin.name == "recursive-guard" or not manifest_path.exists():
                continue
            manifest_text = manifest_path.read_text(encoding="utf-8")
            self.assertNotIn("recursive-guard", manifest_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
