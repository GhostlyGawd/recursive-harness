#!/usr/bin/env python3
"""Contract for receipt-bound Codex consumer acceptance (P-2026-044/045)."""

from __future__ import annotations

import json
from pathlib import Path
import random
import re
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence" / "codex-consumer-acceptance.json"
NARRATIVE = ROOT / "docs" / "codex-consumer-acceptance.md"
PROPOSAL = ROOT / "proposals" / "resolved" / "P-2026-044-noninvasive-capability-suite.md"
RELEASE_COMMIT = "202647e50edea2418773e8005e93630a5b7ca479"
PLUGINS = ("recursive-observe", "recursive-guard")

sys.path.insert(0, str(ROOT / "scripts"))
import record_codex_consumer_acceptance as recorder  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def canonical_receipt(plugin: str) -> dict:
    path = ROOT / "plugins" / plugin / "canonical-source.json"
    return json.loads(path.read_text(encoding="utf-8"))


def property_checks() -> None:
    rng = random.Random(20260719)
    with tempfile.TemporaryDirectory(prefix="codex-acceptance-properties-") as raw_tmp:
        temp_root = Path(raw_tmp)
        first = temp_root / "first"
        second = temp_root / "second"
        first.mkdir()
        second.mkdir()
        payloads = {
            f"group {index % 5}/ü-file-{index:02d}.bin": rng.randbytes(index + 1)
            for index in range(40)
        }
        for root, names in ((first, list(payloads)), (second, list(reversed(payloads)))):
            for name in names:
                target = root / Path(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payloads[name])
        require(recorder.visible_files(first) == recorder.visible_files(second),
                "tree inventory depends on file creation order")
        baseline = recorder.inventory_digest(recorder.visible_files(first))
        require(baseline == recorder.inventory_digest(recorder.visible_files(second)),
                "equivalent trees have different inventory digests")
        (first / ".git" / "objects").mkdir(parents=True)
        (first / ".git" / "objects" / "noise").write_bytes(rng.randbytes(32))
        require(baseline == recorder.inventory_digest(recorder.visible_files(first)),
                "Git internals leaked into the consumer inventory")
        candidate = first / Path(next(iter(payloads)))
        candidate.write_bytes(candidate.read_bytes() + b"tamper")
        require(baseline != recorder.inventory_digest(recorder.visible_files(first)),
                "content mutation did not change the consumer inventory")

        for plugin in PLUGINS:
            copied = temp_root / f"copy-{plugin}"
            shutil.copytree(ROOT / "plugins" / plugin, copied)
            recorder.package_evidence(copied)
            receipt = canonical_receipt(plugin)
            selected = sorted(receipt["package_files"])[rng.randrange(len(receipt["package_files"]))]
            target = copied / Path(selected)
            original = target.read_bytes()
            target.write_bytes(original + b"tamper")
            try:
                recorder.package_evidence(copied)
            except recorder.AcceptanceError:
                pass
            else:
                require(False, f"{plugin} accepted a mutated cached file")
            target.write_bytes(original)
            (copied / "unexpected.payload").write_text("unexpected", encoding="utf-8")
            try:
                recorder.package_evidence(copied)
            except recorder.AcceptanceError:
                pass
            else:
                require(False, f"{plugin} accepted an extra cached file")


def main() -> int:
    property_checks()
    require(EVIDENCE.is_file(), "real Codex consumer receipt is missing")
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    require(data.get("schema_version") == 1, "unexpected acceptance schema")
    require(data.get("result") == "accepted", "Codex consumer run was not accepted")
    require(data.get("release_commit") == RELEASE_COMMIT, "receipt is not pinned to the phase commit")

    consumer = data.get("consumer", {})
    require(consumer.get("package") == "@openai/codex", "consumer package is not official Codex CLI")
    require(re.fullmatch(r"0\.\d+\.\d+", str(consumer.get("version", ""))) is not None,
            "Codex CLI version is not recorded")
    require(consumer.get("plugin_cli") == "stable", "acceptance did not use the stable plugin CLI")

    marketplace = data.get("marketplace", {})
    require(marketplace.get("source") == "GhostlyGawd/recursive-harness", "wrong marketplace source")
    require(marketplace.get("ref") == RELEASE_COMMIT, "marketplace source is mutable")
    require(marketplace.get("name") == "recursive-harness", "wrong marketplace name")

    packages = data.get("packages", {})
    for plugin in PLUGINS:
        actual = packages.get(plugin, {})
        canonical = canonical_receipt(plugin)
        require(actual.get("installed") is True, f"{plugin} was not installed")
        require(actual.get("receipt_verified") is True, f"{plugin} receipt was not verified")
        require(actual.get("package_tree_sha256") == canonical["package_tree_sha256"],
                f"{plugin} package tree differs from canonical receipt")
        require(actual.get("package_files") == canonical["package_files"],
                f"{plugin} file closure differs from canonical receipt")

    repository = data.get("foreign_repository", {})
    require(repository.get("existing_configuration_files") == 7,
            "foreign-repository coexistence fixture is incomplete")
    require(repository.get("before_sha256") == repository.get("after_sha256"),
            "consumer repository changed")
    require(repository.get("git_status_before") == repository.get("git_status_after") == "",
            "consumer Git status changed")
    require(repository.get("repository_writes") == 0, "consumer journey wrote to the repository")

    observe = data.get("observe_journey", {})
    require(observe.get("prediction_scored") == "hit", "Observe journey was not scored")
    require(observe.get("scorecard", {}).get("scored") == 1, "Observe scorecard is not real")
    require(observe.get("state_outside_repository") is True, "Observe state is not outside the repository")

    guard = data.get("guard_journey", {})
    require(guard.get("no_policy") == "exact-noop", "Guard no-policy behavior is not an exact no-op")
    require(guard.get("audit") == "warn-allow", "Guard audit journey was not proven")
    require(guard.get("enforce") == "deny-protected-write", "Guard enforcement journey was not proven")

    require(NARRATIVE.is_file(), "human-readable Codex acceptance record is missing")
    narrative = NARRATIVE.read_text(encoding="utf-8")
    for phrase in ("Codex CLI", RELEASE_COMMIT, "repository writes: 0", "No public marketplace"):
        require(phrase in narrative, f"acceptance narrative is missing: {phrase}")

    proposal = PROPOSAL.read_text(encoding="utf-8")
    require("The Codex adapter passes a real receipt-bound consumer installation and execution" in proposal,
            "P-2026-044 no longer contains its Codex criterion")
    require("- [x] The Codex adapter" in proposal, "P-2026-044 Codex criterion is not complete")
    require("implementation: landed" in proposal, "P-2026-044 is not resolved as landed")

    print("codex consumer acceptance: receipt and claims verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
