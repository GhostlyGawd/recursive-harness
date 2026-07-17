#!/usr/bin/env python3
"""Hermetic smoke tests for installation, account initialization, and launchers."""

# provenance: 2026-07-17 security/productization review — reproduce distribution claims.

from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
FAILURES: list[str] = []
BASH: str | None = None
CAPTURE = {
    "text": True,
    "stdout": subprocess.PIPE,
    "stderr": subprocess.PIPE,
    "check": False,
}


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS  {name}")
    else:
        FAILURES.append(name)
        print(f"FAIL  {name}{': ' + detail if detail else ''}")


def write_executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_bash_launcher() -> None:
    assert BASH is not None
    bash = BASH
    with tempfile.TemporaryDirectory(prefix="harness-launch-") as raw_tmp:
        repo = Path(raw_tmp)
        shutil.copy2(ROOT / "launch.sh", repo / "launch.sh")
        config = repo / ".claude-private" / "accounts" / "dev"
        config.mkdir(parents=True)
        (config / "settings.json").write_text("{}\n", encoding="utf-8")
        fake_bin = repo / "fake-bin"
        write_executable(
            fake_bin / "claude",
            "#!/usr/bin/env bash\nprintf 'CONFIG=%s\\n' \"$CLAUDE_CONFIG_DIR\"\nprintf 'ARGS=%s\\n' \"$*\"\n",
        )
        env = os.environ.copy()
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")

        result = subprocess.run(
            [bash, str(repo / "launch.sh"), "dev", "--", "--version"], cwd=repo, env=env, **CAPTURE
        )
        check("Bash launcher exits with the Claude process", result.returncode == 0, result.stderr)
        check("Bash launcher exports the selected account", "accounts/dev" in result.stdout.replace("\\", "/"))
        check("Bash launcher forwards arguments", "ARGS=--version" in result.stdout, result.stdout)
        check("Bash launcher announces its checkout", "Harness account : dev" in result.stderr, result.stderr)

        missing = subprocess.run([bash, str(repo / "launch.sh"), "missing"], cwd=repo, env=env, **CAPTURE)
        check("Bash launcher refuses an uninitialized account", missing.returncode == 1, missing.stderr)
        invalid = subprocess.run([bash, str(repo / "launch.sh"), "../escape"], cwd=repo, env=env, **CAPTURE)
        check("Bash launcher rejects path-like account names", invalid.returncode == 2, invalid.stderr)


def test_hook_installation() -> None:
    assert BASH is not None
    bash = BASH
    with tempfile.TemporaryDirectory(prefix="harness-install-") as raw_tmp:
        repo = Path(raw_tmp)
        shutil.copy2(ROOT / "install.sh", repo / "install.sh")
        (repo / "lint").mkdir()
        (repo / "lint" / "lint_harness.py").write_text("print('stub lint')\n", encoding="utf-8")
        write_executable(repo / "account-init.sh", "#!/usr/bin/env bash\necho managed-sync\n")
        init = subprocess.run(["git", "init", "-q"], cwd=repo, **CAPTURE)
        check("installer fixture initializes Git", init.returncode == 0, init.stderr)
        hooks_raw = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=repo, **CAPTURE)
        hooks_dir = Path(hooks_raw.stdout.strip())
        if not hooks_dir.is_absolute():
            hooks_dir = repo / hooks_dir
        hooks_dir.mkdir(parents=True, exist_ok=True)
        custom = "#!/usr/bin/env bash\necho custom-hook\nexit 7\n"
        write_executable(hooks_dir / "post-merge", custom)

        first = subprocess.run([bash, str(repo / "install.sh")], cwd=repo.parent, **CAPTURE)
        check("installer succeeds with an existing hook", first.returncode == 0, first.stderr)
        dispatcher = hooks_dir / "post-merge"
        preserved = hooks_dir / "post-merge.d" / "10-existing-post-merge"
        managed = hooks_dir / "post-merge.d" / "50-recursive-harness"
        check("existing post-merge hook is preserved byte-for-byte", preserved.read_text(encoding="utf-8") == custom)
        check("managed hook is installed separately", managed.is_file())
        check(
            "top-level post-merge becomes an explicit dispatcher",
            "recursive-harness managed post-merge dispatcher" in dispatcher.read_text(encoding="utf-8"),
        )

        second = subprocess.run([bash, str(repo / "install.sh")], cwd=repo.parent, **CAPTURE)
        check("hook installation is idempotent", second.returncode == 0, second.stderr)
        check("idempotent install leaves one preserved custom hook", preserved.read_text(encoding="utf-8") == custom)
        dispatched = subprocess.run([bash, str(dispatcher)], cwd=repo, **CAPTURE)
        check("dispatcher runs the preserved custom hook", "custom-hook" in dispatched.stdout, dispatched.stdout)
        check("dispatcher continues to the managed hook", "managed-sync" in dispatched.stdout, dispatched.stdout)
        check("dispatcher preserves custom hook failure semantics", dispatched.returncode == 7, dispatched.stderr)


def test_account_initialization() -> None:
    assert BASH is not None
    bash = BASH
    if os.name == "nt":
        print("SKIP  account symlink/mode smoke test (covered by Ubuntu CI; Windows uses native links)")
        return
    with tempfile.TemporaryDirectory(prefix="harness-account-") as raw_tmp:
        repo = Path(raw_tmp)
        shutil.copy2(ROOT / "account-init.sh", repo / "account-init.sh")
        for name in ("agents", "commands", "hooks", "skills", "templates"):
            (repo / name).mkdir()
        (repo / "templates" / "account-settings.json").write_text(
            '{"_provenance":"fixture","root":"{{REPO_ROOT}}"}\n', encoding="utf-8"
        )
        home = repo / "home"
        home.mkdir()
        env = os.environ.copy()
        env["HOME"] = str(home)

        first = subprocess.run(
            [bash, str(repo / "account-init.sh"), "alpha", "--store-account", "alpha", "--sync-settings"],
            cwd=repo,
            env=env,
            **CAPTURE,
        )
        check("account init creates an explicit store owner", first.returncode == 0, first.stderr)
        private = repo / ".claude-private"
        owner_file = private / "session-store-account"
        check("store-owner choice is persisted", owner_file.read_text(encoding="utf-8").strip() == "alpha")
        check("store-owner config is owner-only", stat.S_IMODE(owner_file.stat().st_mode) == 0o600)
        check("store-owner account gets a real projects directory", (private / "accounts" / "alpha" / "projects").is_dir())
        check("generated settings are owner-only", stat.S_IMODE((private / "accounts" / "alpha" / "settings.json").stat().st_mode) == 0o600)

        second = subprocess.run(
            [bash, str(repo / "account-init.sh"), "beta", "--sync-settings"], cwd=repo, env=env, **CAPTURE
        )
        beta_projects = private / "accounts" / "beta" / "projects"
        check("later accounts reuse the persisted owner", second.returncode == 0 and beta_projects.is_symlink(), second.stderr)
        check("later account store link targets the owner", os.path.realpath(beta_projects) == os.path.realpath(private / "accounts" / "alpha" / "projects"))

        changed_owner = subprocess.run(
            [bash, str(repo / "account-init.sh"), "beta", "--store-account", "beta"],
            cwd=repo,
            env=env,
            **CAPTURE,
        )
        check("account init refuses an unsafe store-owner switch", changed_owner.returncode == 1, changed_owner.stderr)

        again = subprocess.run(
            [bash, str(repo / "account-init.sh"), "alpha", "--sync-settings"], cwd=repo, env=env, **CAPTURE
        )
        backups = list((private / "accounts" / "alpha").glob("settings.json.pre-sync.*"))
        check("settings refresh backs up the previous file", again.returncode == 0 and bool(backups), again.stderr)

        alpha_settings = private / "accounts" / "alpha" / "settings.json"
        external_settings = repo / "external-settings.json"
        external_settings.write_text("unchanged\n", encoding="utf-8")
        alpha_settings.unlink()
        alpha_settings.symlink_to(external_settings)
        linked_settings = subprocess.run(
            [bash, str(repo / "account-init.sh"), "alpha", "--sync-settings"],
            cwd=repo,
            env=env,
            **CAPTURE,
        )
        check("account init refuses a symlinked settings file", linked_settings.returncode == 1, linked_settings.stderr)
        check("settings refusal does not overwrite the external target", external_settings.read_text(encoding="utf-8") == "unchanged\n")

        outside = repo / "outside"
        outside.mkdir()
        outside_env = env.copy()
        outside_env["CLAUDE_CONFIG_DIR"] = str(outside)
        refused = subprocess.run(
            [bash, str(repo / "account-init.sh")], cwd=repo, env=outside_env, **CAPTURE
        )
        check("account init refuses an out-of-silo config directory", refused.returncode == 1, refused.stderr)

        outside_owner = repo / "outside-owner"
        outside_owner.write_text("unchanged\n", encoding="utf-8")
        owner_file.unlink()
        owner_file.symlink_to(outside_owner)
        linked_config = subprocess.run(
            [bash, str(repo / "account-init.sh"), "alpha"], cwd=repo, env=env, **CAPTURE
        )
        check("account init refuses a symlinked store-owner config", linked_config.returncode == 1, linked_config.stderr)
        check("symlink refusal does not overwrite the external target", outside_owner.read_text(encoding="utf-8") == "unchanged\n")


def test_powershell_launcher() -> None:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if not powershell:
        print("SKIP  PowerShell launcher smoke test (PowerShell unavailable)")
        return
    with tempfile.TemporaryDirectory(prefix="harness-launch-ps-") as raw_tmp:
        repo = Path(raw_tmp)
        shutil.copy2(ROOT / "launch.ps1", repo / "launch.ps1")
        config = repo / ".claude-private" / "accounts" / "dev"
        config.mkdir(parents=True)
        (config / "settings.json").write_text("{}\n", encoding="utf-8")
        fake_bin = repo / "fake-bin"
        if os.name == "nt":
            fake_bin.mkdir()
            (fake_bin / "claude.cmd").write_text(
                "@echo off\r\necho CONFIG=%CLAUDE_CONFIG_DIR%\r\necho ARGS=%*\r\n", encoding="ascii"
            )
        else:
            write_executable(
                fake_bin / "claude",
                "#!/usr/bin/env sh\nprintf 'CONFIG=%s\\n' \"$CLAUDE_CONFIG_DIR\"\nprintf 'ARGS=%s\\n' \"$*\"\n",
            )
        env = os.environ.copy()
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
        result = subprocess.run(
            [powershell, "-NoProfile", "-File", str(repo / "launch.ps1"), "dev", "--version"],
            cwd=repo,
            env=env,
            **CAPTURE,
        )
        check("PowerShell launcher exits with the Claude process", result.returncode == 0, result.stderr)
        check("PowerShell launcher exports the selected account", "accounts/dev" in result.stdout.replace("\\", "/"))
        check("PowerShell launcher forwards arguments", "ARGS=--version" in result.stdout, result.stdout)
        check("PowerShell launcher announces its account", "Harness account : dev" in result.stderr, result.stderr)


def find_bash() -> str | None:
    discovered = shutil.which("bash")
    if discovered:
        return discovered
    if os.name == "nt":
        for root_name in ("ProgramFiles", "LOCALAPPDATA"):
            root = os.environ.get(root_name)
            if not root:
                continue
            candidates = [Path(root) / "Git" / "bin" / "bash.exe"]
            if root_name == "LOCALAPPDATA":
                candidates.append(Path(root) / "Programs" / "Git" / "bin" / "bash.exe")
            for candidate in candidates:
                if candidate.is_file():
                    return str(candidate)
    return None


def main() -> int:
    global BASH
    BASH = find_bash()
    if not BASH:
        print("FAIL  Bash is required for distribution smoke tests")
        return 1
    test_bash_launcher()
    test_hook_installation()
    test_account_initialization()
    test_powershell_launcher()
    if FAILURES:
        print(f"\ntest_distribution: {len(FAILURES)} failure(s): {', '.join(FAILURES)}", file=sys.stderr)
        return 1
    print("\ntest_distribution: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
