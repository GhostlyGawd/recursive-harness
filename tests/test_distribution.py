#!/usr/bin/env python3
"""Hermetic smoke tests for installation, account initialization, and launchers."""

# provenance: 2026-07-17 security/productization review — reproduce distribution claims.

from __future__ import annotations

import os
from pathlib import Path
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FAILURES: list[str] = []
BASH_COMMAND = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else "/usr/bin/bash"
POWERSHELL_COMMAND = "powershell" if os.name == "nt" else "pwsh"
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
            [BASH_COMMAND, str(repo / "launch.sh"), "dev", "--", "--version"], cwd=repo, env=env, **CAPTURE
        )
        check("Bash launcher exits with the Claude process", result.returncode == 0, result.stderr)
        check("Bash launcher exports the selected account", "accounts/dev" in result.stdout.replace("\\", "/"))
        check("Bash launcher forwards arguments", "ARGS=--version" in result.stdout, result.stdout)
        check("Bash launcher announces its checkout", "Harness account : dev" in result.stderr, result.stderr)

        missing = subprocess.run([BASH_COMMAND, str(repo / "launch.sh"), "missing"], cwd=repo, env=env, **CAPTURE)
        check("Bash launcher refuses an uninitialized account", missing.returncode == 1, missing.stderr)
        invalid = subprocess.run([BASH_COMMAND, str(repo / "launch.sh"), "../escape"], cwd=repo, env=env, **CAPTURE)
        check("Bash launcher rejects path-like account names", invalid.returncode == 2, invalid.stderr)


def test_hook_installation() -> None:
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

        first = subprocess.run([BASH_COMMAND, str(repo / "install.sh")], cwd=repo.parent, **CAPTURE)
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

        second = subprocess.run([BASH_COMMAND, str(repo / "install.sh")], cwd=repo.parent, **CAPTURE)
        check("hook installation is idempotent", second.returncode == 0, second.stderr)
        check("idempotent install leaves one preserved custom hook", preserved.read_text(encoding="utf-8") == custom)
        dispatched = subprocess.run([BASH_COMMAND, str(dispatcher)], cwd=repo, **CAPTURE)
        check("dispatcher runs the preserved custom hook", "custom-hook" in dispatched.stdout, dispatched.stdout)
        check("dispatcher continues to the managed hook", "managed-sync" in dispatched.stdout, dispatched.stdout)
        check("dispatcher preserves custom hook failure semantics", dispatched.returncode == 7, dispatched.stderr)


def test_uninstall() -> None:
    with tempfile.TemporaryDirectory(prefix="harness-uninstall-") as raw_tmp:
        repo = Path(raw_tmp)
        shutil.copy2(ROOT / "install.sh", repo / "install.sh")
        shutil.copy2(ROOT / "uninstall.sh", repo / "uninstall.sh")
        (repo / "lint").mkdir()
        (repo / "lint" / "lint_harness.py").write_text("print('stub lint')\n", encoding="utf-8")
        write_executable(repo / "account-init.sh", "#!/usr/bin/env bash\necho managed-sync\n")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        hooks_raw = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=repo, **CAPTURE)
        hooks_dir = Path(hooks_raw.stdout.strip())
        if not hooks_dir.is_absolute():
            hooks_dir = repo / hooks_dir
        hooks_dir.mkdir(parents=True, exist_ok=True)
        custom = "#!/usr/bin/env bash\necho user-hook\n"
        write_executable(hooks_dir / "post-merge", custom)

        installed = subprocess.run([BASH_COMMAND, str(repo / "install.sh")], cwd=repo, **CAPTURE)
        check("uninstall fixture installs managed wiring", installed.returncode == 0, installed.stderr)
        removed = subprocess.run([BASH_COMMAND, str(repo / "uninstall.sh")], cwd=repo, **CAPTURE)
        check("uninstall exits successfully", removed.returncode == 0, removed.stderr)
        check("uninstall restores the user-owned post-merge hook", (hooks_dir / "post-merge").read_text(encoding="utf-8") == custom)
        check("uninstall removes its managed task directory", not (hooks_dir / "post-merge.d").exists())

        if os.name != "nt":
            account = repo / ".claude-private" / "accounts" / "dev"
            account.mkdir(parents=True)
            (account / "settings.json").write_text("{}\n", encoding="utf-8")
            (repo / "skills").mkdir()
            (account / "skills").symlink_to(repo / "skills", target_is_directory=True)
            account_removed = subprocess.run(
                [BASH_COMMAND, str(repo / "uninstall.sh"), "--account", "dev"], cwd=repo, **CAPTURE
            )
            check("account uninstall exits successfully", account_removed.returncode == 0, account_removed.stderr)
            check("account uninstall removes managed links", not (account / "skills").exists())
            check("account uninstall preserves settings", (account / "settings.json").read_text(encoding="utf-8") == "{}\n")


def test_release_archives() -> None:
    with tempfile.TemporaryDirectory(prefix="harness-release-") as raw_tmp:
        workspace = Path(raw_tmp)
        repo = workspace / "repo"
        repo.mkdir()
        (repo / "VERSION").write_text("9.8.7\n", encoding="utf-8")
        (repo / "LICENSE").write_text("fixture license\n", encoding="utf-8")
        (repo / "run.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
        (repo / "run.sh").chmod(0o755)
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": "Harness Test",
                "GIT_AUTHOR_EMAIL": "harness@example.invalid",
                "GIT_COMMITTER_NAME": "Harness Test",
                "GIT_COMMITTER_EMAIL": "harness@example.invalid",
                "GIT_AUTHOR_DATE": "2026-01-02T03:04:05Z",
                "GIT_COMMITTER_DATE": "2026-01-02T03:04:05Z",
            }
        )
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=repo, check=True, env=env)

        outputs = []
        for name in ("one", "two"):
            output = workspace / name
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_release.py"), "--repo", str(repo), "--output", str(output)],
                cwd=repo,
                **CAPTURE,
            )
            check(f"release builder creates {name} archive set", result.returncode == 0, result.stderr)
            outputs.append(output)

        names = ["recursive-harness-v9.8.7.tar.gz", "recursive-harness-v9.8.7.zip"]
        for artifact_name in names:
            first = (outputs[0] / artifact_name).read_bytes()
            second = (outputs[1] / artifact_name).read_bytes()
            check(f"release artifact is reproducible: {artifact_name}", hashlib.sha256(first).digest() == hashlib.sha256(second).digest())

        zip_path = outputs[0] / names[1]
        with zipfile.ZipFile(zip_path) as archive:
            archive_names = set(archive.namelist())
            manifest_data = json.loads(archive.read("recursive-harness-v9.8.7/RELEASE-MANIFEST.json"))
        check("release ZIP contains the root license", "recursive-harness-v9.8.7/LICENSE" in archive_names)
        check("release manifest records the exact committed revision", manifest_data["revision"] == subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True, check=True).stdout.strip())

        tar_path = outputs[0] / names[0]
        with tarfile.open(tar_path, "r:gz") as archive:
            tar_names = set(archive.getnames())
        check("release tarball contains the root license", "recursive-harness-v9.8.7/LICENSE" in tar_names)

        checksum_lines = (outputs[0] / "recursive-harness-v9.8.7.sha256").read_text(encoding="ascii").splitlines()
        check("release bundle publishes one checksum per archive", len(checksum_lines) == 2)


def test_account_initialization() -> None:
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
            [BASH_COMMAND, str(repo / "account-init.sh"), "alpha", "--store-account", "alpha", "--sync-settings"],
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
            [BASH_COMMAND, str(repo / "account-init.sh"), "beta", "--sync-settings"], cwd=repo, env=env, **CAPTURE
        )
        beta_projects = private / "accounts" / "beta" / "projects"
        check("later accounts reuse the persisted owner", second.returncode == 0 and beta_projects.is_symlink(), second.stderr)
        check("later account store link targets the owner", os.path.realpath(beta_projects) == os.path.realpath(private / "accounts" / "alpha" / "projects"))

        changed_owner = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh"), "beta", "--store-account", "beta"],
            cwd=repo,
            env=env,
            **CAPTURE,
        )
        check("account init refuses an unsafe store-owner switch", changed_owner.returncode == 1, changed_owner.stderr)

        again = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh"), "alpha", "--sync-settings"], cwd=repo, env=env, **CAPTURE
        )
        backups = list((private / "accounts" / "alpha").glob("settings.json.pre-sync.*"))
        check("settings refresh backs up the previous file", again.returncode == 0 and bool(backups), again.stderr)

        alpha_settings = private / "accounts" / "alpha" / "settings.json"
        external_settings = repo / "external-settings.json"
        external_settings.write_text("unchanged\n", encoding="utf-8")
        alpha_settings.unlink()
        alpha_settings.symlink_to(external_settings)
        linked_settings = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh"), "alpha", "--sync-settings"],
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
            [BASH_COMMAND, str(repo / "account-init.sh")], cwd=repo, env=outside_env, **CAPTURE
        )
        check("account init refuses an out-of-silo config directory", refused.returncode == 1, refused.stderr)

        outside_owner = repo / "outside-owner"
        outside_owner.write_text("unchanged\n", encoding="utf-8")
        owner_file.unlink()
        owner_file.symlink_to(outside_owner)
        linked_config = subprocess.run(
            [BASH_COMMAND, str(repo / "account-init.sh"), "alpha"], cwd=repo, env=env, **CAPTURE
        )
        check("account init refuses a symlinked store-owner config", linked_config.returncode == 1, linked_config.stderr)
        check("symlink refusal does not overwrite the external target", outside_owner.read_text(encoding="utf-8") == "unchanged\n")


def test_powershell_launcher() -> None:
    if not shutil.which(POWERSHELL_COMMAND):
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
            [POWERSHELL_COMMAND, "-NoProfile", "-File", str(repo / "launch.ps1"), "dev", "--version"],
            cwd=repo,
            env=env,
            **CAPTURE,
        )
        check("PowerShell launcher exits with the Claude process", result.returncode == 0, result.stderr)
        check("PowerShell launcher exports the selected account", "accounts/dev" in result.stdout.replace("\\", "/"))
        check("PowerShell launcher forwards arguments", "ARGS=--version" in result.stdout, result.stdout)
        check("PowerShell launcher announces its account", "Harness account : dev" in result.stderr, result.stderr)


def main() -> int:
    if not Path(BASH_COMMAND).is_file():
        print("FAIL  Bash is required for distribution smoke tests")
        return 1
    test_bash_launcher()
    test_hook_installation()
    test_uninstall()
    test_release_archives()
    test_account_initialization()
    test_powershell_launcher()
    if FAILURES:
        print(f"\ntest_distribution: {len(FAILURES)} failure(s): {', '.join(FAILURES)}", file=sys.stderr)
        return 1
    print("\ntest_distribution: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
