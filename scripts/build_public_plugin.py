#!/usr/bin/env python3
"""Build and validate the deterministic Recursive public skills plugin."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import NamedTuple
from urllib.parse import urlparse
import zipfile


ROOT = Path(__file__).resolve().parent.parent
METADATA = ROOT / "marketplace" / "recursive"
RELEASE_REF = "v0.1.2"
RELEASE_COMMIT = "5a524d199d6c061a30fa577fbfe6ed0cb7b9a0d4"
CAPABILITIES = ("observe", "learn", "verify", "coordinate")
OFFICIAL_REQUIREMENTS = "https://learn.chatgpt.com/docs/submit-plugins"
ALLOWED_PUBLIC_URLS = {
    "https://github.com/GhostlyGawd/recursive-harness",
    "https://github.com/GhostlyGawd/recursive-harness/releases/tag/v0.1.2",
    "https://github.com/GhostlyGawd/recursive-harness/blob/main/SUPPORT.md",
    "https://github.com/GhostlyGawd/recursive-harness/blob/main/PRIVACY.md",
    "https://github.com/GhostlyGawd/recursive-harness/blob/main/LICENSE",
}
TEXT_SECRET_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)https://[^\s/?#]+:[^\s/@]+@"),
    re.compile(r"(?i)(?:C:[\\/]Users[\\/]|/home/|/Users/)[^\s/\\]+"),
)
CASE_FIELDS = {
    "positive": {"id", "skill", "prompt", "expected_behavior", "expected_result_shape", "fixture"},
    "negative": {"id", "prompt", "expected_behavior", "reason"},
}


class SubmissionError(RuntimeError):
    """A public submission invariant was violated."""


class BuildResult(NamedTuple):
    archive: Path
    checksum: Path
    receipt_path: Path
    receipt: dict[str, object]


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def run_git(*args: str) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise SubmissionError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def git_file(commit: str, path: str) -> bytes:
    return run_git("show", f"{commit}:{path}")


def git_files(commit: str, prefix: str) -> list[str]:
    output = run_git("ls-tree", "-r", "--name-only", commit, "--", prefix)
    return [line for line in output.decode("utf-8").splitlines() if line]


def all_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from all_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_strings(child)


def safe_member(name: str) -> bool:
    if not name or "\\" in name or "\x00" in name:
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def confined_relative_path(value: str) -> bool:
    return value == PurePosixPath(value).as_posix() and safe_member(value) and ":" not in value


def canonical_public_url(value: object) -> bool:
    if not isinstance(value, str) or value not in ALLOWED_PUBLIC_URLS:
        return False
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "github.com"
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SubmissionError(message)


def validate_submission_data(listing: dict, cases: dict) -> None:
    require(listing.get("schema_version") == 1, "listing schema must be version 1")
    source = listing.get("source", {})
    require(source.get("repository") == "GhostlyGawd/recursive-harness", "wrong canonical repository")
    require(source.get("ref") == RELEASE_REF and source.get("commit") == RELEASE_COMMIT,
            "source must use the immutable release tag and commit")
    require(canonical_public_url(source.get("release_url")), "release URL is not a public canonical URL")

    plugin = listing.get("plugin", {})
    require(plugin.get("id") == "recursive", "public plugin id must be recursive")
    require(plugin.get("version") == "0.1.2", "public plugin version must be 0.1.2")
    require(plugin.get("display_name") == "Recursive", "public display name must be Recursive")
    require(1 <= len(plugin.get("short_description", "")) <= 80,
            "short description must contain 1-80 characters")
    require(80 <= len(plugin.get("long_description", "")) <= 600,
            "long description must contain 80-600 characters")
    require(plugin.get("category") == "Developer Tools", "wrong public category")
    require(set(plugin.get("skills", [])) == set(CAPABILITIES), "public bundle capability set changed")
    require(plugin.get("components") == {"skills": "./skills/"},
            "public package must remain skills-only")
    require(plugin.get("brand_color") == "#20D9FF", "brand color does not match Recursive")
    for field in ("logo_path", "screenshot_path"):
        require(confined_relative_path(str(plugin.get(field, ""))),
                f"{field} must be a confined relative path")
    for field in ("website_url", "support_url", "privacy_policy_url", "terms_url"):
        require(canonical_public_url(plugin.get(field)), f"{field} must be a public canonical URL")

    require(len(listing.get("starter_prompts", [])) >= 3, "at least three starter prompts are required")
    runtime = listing.get("runtime", {})
    require(runtime.get("authentication") == "none" and runtime.get("network") == "none",
            "skills-only package must not claim authentication or network access")
    require(runtime.get("repository_writes_by_default") is False,
            "repository writes must remain disabled by default")
    availability = listing.get("availability", {})
    require(availability.get("status") in {"owner-selection-required", "selected"},
            "availability state is invalid")
    require(isinstance(availability.get("countries"), list), "availability countries must be a list")

    require(cases.get("schema_version") == 1, "evaluator schema must be version 1")
    positives = cases.get("positive", [])
    negatives = cases.get("negative", [])
    require(len(positives) == 5, "submission requires exactly five positive test cases")
    require(len(negatives) == 3, "submission requires exactly three negative test cases")
    identifiers: list[str] = []
    signatures: list[str] = []
    for kind, records in (("positive", positives), ("negative", negatives)):
        for record in records:
            require(isinstance(record, dict) and set(record) == CASE_FIELDS[kind],
                    f"{kind} test case fields are incomplete or unexpected")
            require(all(isinstance(value, str) and value.strip() for value in record.values()),
                    f"{kind} test case fields must be non-empty strings")
            identifiers.append(record["id"])
            signatures.append(json.dumps(record, sort_keys=True, ensure_ascii=False))
    require(len(identifiers) == len(set(identifiers)) and len(signatures) == len(set(signatures)),
            "evaluator test cases must be distinct")
    require(set(record["skill"] for record in positives) == set(CAPABILITIES),
            "positive test cases must cover all public skills")

    for value in all_strings(listing):
        require(not any(pattern.search(value) for pattern in TEXT_SECRET_PATTERNS),
                "submission metadata contains a secret-like or private string")


def verify_provider(commit: str, capability: str) -> tuple[dict, list[str]]:
    root = f"plugins/recursive-{capability}"
    receipt = json.loads(git_file(commit, f"{root}/canonical-source.json"))
    require(receipt.get("capability") == f"recursive-{capability}",
            f"{capability} canonical receipt names the wrong capability")
    expected = receipt.get("package_files", {})
    require(isinstance(expected, dict) and expected, f"{capability} canonical receipt is empty")
    actual = set(git_files(commit, root))
    expected_paths = {f"{root}/{path}" for path in expected} | {f"{root}/canonical-source.json"}
    require(actual == expected_paths, f"{capability} release package has unreceipted files")
    for relative, expected_hash in expected.items():
        actual_hash = sha256(normalized(git_file(commit, f"{root}/{relative}")))
        require(actual_hash == expected_hash, f"{capability} release package receipt mismatch: {relative}")
    skill_prefix = f"{root}/skills/{capability}/"
    skill_files = [path for path in sorted(actual) if path.startswith(skill_prefix)]
    require(f"{skill_prefix}SKILL.md" in skill_files, f"{capability} release skill is missing SKILL.md")
    return receipt, skill_files


def manifest_from(listing: dict) -> dict:
    plugin = listing["plugin"]
    return {
        "name": plugin["id"],
        "version": plugin["version"],
        "description": plugin["short_description"],
        "author": {
            "name": plugin["developer_name"],
            "url": "https://github.com/GhostlyGawd",
        },
        "homepage": plugin["website_url"],
        "repository": "https://github.com/GhostlyGawd/recursive-harness",
        "license": "MIT",
        "keywords": ["agents", "calibration", "learning", "verification", "coordination"],
        "skills": "./skills/",
        "interface": {
            "displayName": plugin["display_name"],
            "shortDescription": plugin["short_description"],
            "longDescription": plugin["long_description"],
            "developerName": plugin["developer_name"],
            "category": plugin["category"],
            "capabilities": plugin["capabilities"],
            "websiteURL": plugin["website_url"],
            "privacyPolicyURL": plugin["privacy_policy_url"],
            "termsOfServiceURL": plugin["terms_url"],
            "defaultPrompt": listing["starter_prompts"],
            "brandColor": plugin["brand_color"],
            "composerIcon": f"./{plugin['logo_path']}",
            "logo": f"./{plugin['logo_path']}",
            "screenshots": [f"./{plugin['screenshot_path']}"],
        },
    }


def bundle_files(listing: dict) -> tuple[dict[str, bytes], dict[str, object]]:
    commit = run_git("rev-parse", f"{RELEASE_REF}^{{commit}}").decode("ascii").strip()
    require(commit == RELEASE_COMMIT, "release tag does not resolve to the approved release commit")
    files: dict[str, bytes] = {
        ".codex-plugin/plugin.json": canonical_json(manifest_from(listing)),
        "LICENSE": git_file(commit, "LICENSE"),
        "SUPPORT.md": git_file(commit, "SUPPORT.md"),
        "assets/recursive-mark.svg": git_file(commit, "brand/identity/mark.svg"),
        "assets/recursive-overview.png": git_file(commit, "brand/applications/social-preview.png"),
    }
    provider_receipts = {}
    source_files = {}
    for capability in CAPABILITIES:
        provider, paths = verify_provider(commit, capability)
        provider_receipts[capability] = {
            "package_tree_sha256": provider["package_tree_sha256"],
            "source_tree_sha256": provider["source_tree_sha256"],
        }
        prefix = f"plugins/recursive-{capability}/skills/{capability}/"
        for source_path in paths:
            target = f"skills/{capability}/{source_path.removeprefix(prefix)}"
            data = git_file(commit, source_path)
            files[target] = data
            source_files[source_path] = {"bundled_path": target, "sha256": sha256(normalized(data))}
    for name, data in files.items():
        if Path(name).suffix.lower() not in {".json", ".md", ".py", ".svg", ".yaml", ".yml", ""}:
            continue
        text = data.decode("utf-8", errors="strict")
        require(not any(pattern.search(text) for pattern in TEXT_SECRET_PATTERNS),
                f"bundle file contains a secret-like or private string: {name}")
    payload_hashes = {name: sha256(data) for name, data in sorted(files.items())}
    receipt = {
        "schema_version": 1,
        "result": "verified",
        "source_repository": listing["source"]["repository"],
        "source_ref": RELEASE_REF,
        "source_commit": RELEASE_COMMIT,
        "release_url": listing["source"]["release_url"],
        "capabilities": list(CAPABILITIES),
        "provider_receipts": provider_receipts,
        "source_files": source_files,
        "payload_files": payload_hashes,
        "payload_tree_sha256": sha256(canonical_json(payload_hashes)),
        "side_effects": {
            "repository_setup": "none",
            "hooks": "none",
            "network": "none",
            "private_sidecar": "Observe, Learn, and Coordinate commands write only to ~/.recursive-harness",
            "destructive_commands": "privacy deletion remains dry-run until explicit --apply",
        },
    }
    files["BUNDLE-RECEIPT.json"] = canonical_json(receipt)
    return files, receipt


def write_archive(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            require(safe_member(name), f"unsafe bundle path: {name}")
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if name.endswith(".py") else 0o644
            info.external_attr = (mode & 0xFFFF) << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(output_dir: Path) -> BuildResult:
    listing = json.loads((METADATA / "listing.json").read_text(encoding="utf-8"))
    cases = json.loads((METADATA / "evaluator-cases.json").read_text(encoding="utf-8"))
    validate_submission_data(listing, cases)
    files, bundle_receipt = bundle_files(listing)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / "recursive-plugin-0.1.2.zip"
    write_archive(archive, files)
    archive_hash = sha256(archive.read_bytes())
    external_receipt = {
        "schema_version": 1,
        "result": "verified",
        "archive": archive.name,
        "archive_sha256": archive_hash,
        "archive_bytes": archive.stat().st_size,
        "bundle_receipt_sha256": sha256(files["BUNDLE-RECEIPT.json"]),
        "payload_tree_sha256": bundle_receipt["payload_tree_sha256"],
        "source_ref": RELEASE_REF,
        "source_commit": RELEASE_COMMIT,
        "official_requirements": OFFICIAL_REQUIREMENTS,
        "evaluator_cases": {"positive": len(cases["positive"]), "negative": len(cases["negative"])},
    }
    checksum = archive.with_suffix(".zip.sha256")
    receipt_path = archive.with_suffix(".zip.receipt.json")
    checksum.write_text(f"{archive_hash}  {archive.name}\n", encoding="utf-8", newline="\n")
    receipt_path.write_bytes(canonical_json(external_receipt))
    return BuildResult(archive, checksum, receipt_path, external_receipt)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist" / "public-plugin")
    args = parser.parse_args()
    try:
        result = build(args.output_dir)
    except (SubmissionError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"built {result.archive}")
    print(f"sha256 {result.receipt['archive_sha256']}")
    print("public plugin bundle verified: skills-only, release-pinned, reproducible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
