#!/usr/bin/env python3
"""Raw-byte and Windows checkout contract for Recursive Observe."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "recursive-observe"
RECEIPT = PLUGIN / "canonical-source.json"
PRE_ATTRIBUTE_COMMIT = "5bed2286b5ecaaae25de98710f5a5dbc6e6dd7dc"
LIVE_COMMIT = "ca5f79c69777ae72f2d70ea79332e3702734d457"
LIVE_EVIDENCE = (
    ROOT / "docs" / "evidence"
    / "observe-codex-windows-raw-byte-acceptance-2026-07-29.json"
)
LIVE_NARRATIVE = ROOT / "docs" / "observe-codex-windows-raw-byte-acceptance-2026-07-29.md"

sys.path.insert(0, str(ROOT / "scripts"))
import record_codex_consumer_acceptance as recorder  # noqa: E402
import record_observe_codex_windows_acceptance as windows_recorder  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    require(result.returncode == 0, f"{' '.join(command)} failed: {result.stderr.strip()}")
    return result


def expect_receipt_failure(plugin_root: Path, message: str) -> None:
    try:
        recorder.package_evidence(plugin_root)
    except recorder.AcceptanceError:
        return
    raise AssertionError(message)


def receipt_paths(receipt: dict[str, object]) -> list[str]:
    sources = receipt["sources"]
    packages = receipt["package_files"]
    require(isinstance(sources, dict), "receipt sources are not an object")
    require(isinstance(packages, dict), "receipt package files are not an object")
    paths = set(sources)
    paths.update(f"plugins/recursive-observe/{name}" for name in packages)
    paths.add("plugins/recursive-observe/canonical-source.json")
    return sorted(paths)


def checkout_with_autocrlf(paths: list[str], destination: Path) -> None:
    staging = destination.parent / "staging"
    staging.mkdir()
    shutil.copy2(ROOT / ".gitattributes", staging / ".gitattributes")
    for name in paths:
        source = ROOT / Path(name)
        target = staging / Path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    run(["git", "init", "--quiet"], cwd=staging)
    run(["git", "-c", "core.autocrlf=false", "add", "."], cwd=staging)
    destination.mkdir()
    run([
        "git", "-c", "core.autocrlf=true", "checkout-index", "--all", "--force",
        f"--prefix={destination.as_posix()}/",
    ], cwd=staging)


def raw_receipt_checks(receipt: dict[str, object], plugin_root: Path) -> None:
    require(receipt.get("contract_version") == 2, "Observe receipt is not contract version 2")
    require(receipt.get("hash_semantics") == "sha256-raw-bytes",
            "Observe receipt does not declare raw-byte SHA-256")
    expected = receipt["package_files"]
    require(isinstance(expected, dict), "receipt package files are not an object")
    actual = {
        name: hashlib.sha256((plugin_root / Path(name)).read_bytes()).hexdigest()
        for name in sorted(expected)
    }
    require(actual == expected, "raw package bytes do not match the Observe receipt")
    recorder.package_evidence(plugin_root)


def main() -> int:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    paths = receipt_paths(receipt)
    attributes = run(
        ["git", "check-attr", "text", "eol", "--", *paths],
        cwd=ROOT,
    ).stdout.splitlines()
    require(len(attributes) == len(paths) * 2, "Git did not report both attributes for every path")
    require(all(line.endswith(": text: set") or line.endswith(": eol: lf") for line in attributes),
            "an Observe receipt path is not forced to LF text")
    transition_paths = [
        f"plugins/recursive-observe/{name}"
        for name in receipt["package_files"]
    ]
    transition_paths.append("plugins/recursive-observe/canonical-source.json")
    for name in transition_paths:
        baseline = subprocess.run(
            ["git", "show", f"{PRE_ATTRIBUTE_COMMIT}:{name}"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require(baseline.returncode == 0, f"cannot read pre-attribute blob for {name}")
        require(
            baseline.stdout != (ROOT / Path(name)).read_bytes(),
            f"{name} did not change after the pre-attribute checkout",
        )

    raw_receipt_checks(receipt, PLUGIN)
    recorder_source = (
        ROOT / "scripts" / "record_observe_codex_windows_acceptance.py"
    ).read_text(encoding="utf-8")
    require(
        'source_ref = f"{int(source_ref, 16):040x}"' in recorder_source,
        "Windows acceptance does not canonicalize the commit ref before command use",
    )
    require(
        "--scratch-root" not in recorder_source and "dir=scratch_root" not in recorder_source,
        "Windows acceptance still accepts an arbitrary temporary-directory parent",
    )

    with tempfile.TemporaryDirectory(prefix="observe-raw-byte-") as raw_tmp:
        temp_root = Path(raw_tmp)
        checkout = temp_root / "autocrlf-checkout"
        checkout_with_autocrlf(paths, checkout)
        checkout_receipt = json.loads(
            (checkout / "plugins/recursive-observe/canonical-source.json").read_text(encoding="utf-8")
        )
        raw_receipt_checks(checkout_receipt, checkout / "plugins/recursive-observe")

        copied = temp_root / "mutated"
        shutil.copytree(PLUGIN, copied)
        selected = copied / "skills" / "observe" / "SKILL.md"
        original = selected.read_bytes()
        require(b"\n" in original, "selected receipt fixture has no LF to mutate")
        selected.write_bytes(original.replace(b"\n", b"\r\n", 1))
        expect_receipt_failure(copied, "version 2 accepted a CRLF-only mutation")

        selected.write_bytes(original + b"tamper")
        expect_receipt_failure(copied, "version 2 accepted a content mutation")
        selected.write_bytes(original)
        selected.unlink()
        expect_receipt_failure(copied, "version 2 accepted a missing file")

        shutil.copytree(PLUGIN, copied, dirs_exist_ok=True)
        (copied / "unexpected.payload").write_bytes(b"unexpected")
        expect_receipt_failure(copied, "version 2 accepted an extra file")

        historical = temp_root / "historical-v1"
        shutil.copytree(PLUGIN, historical)
        historical_receipt_path = historical / "canonical-source.json"
        historical_receipt = json.loads(historical_receipt_path.read_text(encoding="utf-8"))
        historical_receipt["contract_version"] = 1
        historical_receipt.pop("hash_semantics", None)
        historical_receipt_path.write_text(
            json.dumps(historical_receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        historical_target = historical / "skills" / "observe" / "SKILL.md"
        historical_target.write_bytes(historical_target.read_bytes().replace(b"\n", b"\r\n", 1))
        recorder.package_evidence(historical)

        malformed = temp_root / "malformed-receipt"
        shutil.copytree(PLUGIN, malformed)
        malformed_receipt_path = malformed / "canonical-source.json"
        malformed_receipt = json.loads(malformed_receipt_path.read_text(encoding="utf-8"))
        malformed_receipt["contract_version"] = True
        malformed_receipt_path.write_text(
            json.dumps(malformed_receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        expect_receipt_failure(malformed, "boolean receipt contract version was accepted")

        malformed_receipt["contract_version"] = 2
        malformed_receipt.pop("hash_semantics")
        malformed_receipt_path.write_text(
            json.dumps(malformed_receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        expect_receipt_failure(malformed, "version 2 without raw-byte semantics was accepted")

        foreign = temp_root / "foreign-repository"
        windows_recorder.create_clean_foreign_repository(foreign)
        require(
            run(["git", "status", "--porcelain"], cwd=foreign).stdout == "",
            "commit-free foreign repository fixture is not clean",
        )

        protected_home = temp_root / "protected-home"
        codex_config = protected_home / ".codex" / "config.toml"
        observe_ledger = (
            protected_home / ".recursive-harness" / "observe" / "predictions.jsonl"
        )
        codex_config.parent.mkdir(parents=True)
        observe_ledger.parent.mkdir(parents=True)
        codex_config.write_bytes(b"model = \"fixture\"\n")
        observe_ledger.write_bytes(b"{\"fixture\":true}\n")
        protected_before = windows_recorder.protected_snapshot(protected_home)
        comparison = windows_recorder.protected_comparison(
            protected_before,
            windows_recorder.protected_snapshot(protected_home),
        )
        require(
            all(all(result.values()) for result in comparison.values()),
            "unchanged protected files did not compare equal",
        )
        codex_config.write_bytes(codex_config.read_bytes() + b"# changed\n")
        try:
            windows_recorder.protected_comparison(
                protected_before,
                windows_recorder.protected_snapshot(protected_home),
            )
        except recorder.AcceptanceError:
            pass
        else:
            require(False, "protected user-state mutation was accepted")

    require(LIVE_EVIDENCE.is_file(), "Windows raw-byte acceptance evidence is missing")
    evidence = json.loads(LIVE_EVIDENCE.read_text(encoding="utf-8"))
    require(evidence.get("result") == "accepted", "Windows raw-byte acceptance did not pass")
    require(evidence.get("source_commit") == LIVE_COMMIT,
            "Windows raw-byte acceptance uses the wrong commit")
    require(evidence.get("host") == {
        "git_core_autocrlf": "true",
        "platform": "Windows",
        "python": "3.12.10",
    }, "Windows raw-byte acceptance has the wrong host contract")
    require(
        evidence.get("consumer", {}).get("version") == "0.145.0",
        "Windows raw-byte acceptance has the wrong Codex version",
    )
    package = evidence.get("package", {})
    require(
        package.get("contract_version") == 2
        and package.get("hash_semantics") == "sha256-raw-bytes"
        and package.get("package_tree_sha256") == receipt["package_tree_sha256"]
        and package.get("files_verified") == len(receipt["package_files"])
        and package.get("hooks") is False
        and package.get("other_recursive_plugins_installed") is False,
        "Windows installed-package evidence differs from the current receipt",
    )
    scorecard = evidence.get("journeys", {}).get("scorecard", {})
    require(scorecard == {
        "brier": 0.27,
        "hits": 2,
        "pending": 0,
        "scored": 3,
        "total": 3,
    }, "Windows Observe journey evidence is incomplete")
    repository = evidence.get("foreign_repository", {})
    require(
        repository.get("before_sha256") == repository.get("after_sha256")
        and repository.get("git_status_before") == repository.get("git_status_after") == ""
        and repository.get("repository_writes") == 0,
        "Windows consumer repository evidence is not zero-write",
    )
    protected = evidence.get("protected_user_state", {})
    require(
        protected
        and all(
            set(result) == {
                "existence_unchanged", "size_unchanged", "sha256_unchanged"
            }
            and all(result.values())
            for result in protected.values()
        ),
        "protected user-state evidence is not equality-only and unchanged",
    )
    require(evidence.get("rollback") == {
        "isolated_sidecar_preserved_until_temporary_cleanup": True,
        "marketplace_removed": True,
        "plugin_removed": True,
    }, "Windows acceptance rollback is incomplete")
    require(
        evidence.get("limitations", {}).get("global_install") == "not performed"
        and evidence.get("limitations", {}).get("public_marketplace") == "not tested"
        and evidence.get("limitations", {}).get("release") == "not tested",
        "Windows acceptance overstates its scope",
    )
    require(LIVE_NARRATIVE.is_file(), "Windows raw-byte acceptance narrative is missing")
    narrative = LIVE_NARRATIVE.read_text(encoding="utf-8")
    for phrase in (
        "Codex CLI 0.145.0",
        LIVE_COMMIT,
        "repository writes: 0",
        "No global plugin installation occurred",
        "Human review, merge, and protected-main CI remain pending",
    ):
        require(phrase in narrative, f"Windows acceptance narrative is missing: {phrase}")

    print("Observe raw-byte distribution: contract and Windows checkout verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
