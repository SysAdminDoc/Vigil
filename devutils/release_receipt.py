#!/usr/bin/env python3
"""Create and validate a hash/provenance receipt for Vigil artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RECEIPT_SCHEMA_VERSION = 1
ARCHITECTURES = ("x64", "x86", "arm64")
ARTIFACT_SUFFIXES = {".exe": "installer", ".msi": "msi", ".zip": "archive"}
PLACEHOLDER_RE = re.compile(r"TODO_FILL_BEFORE_PR|0{64}", re.IGNORECASE)


class ReceiptError(RuntimeError):
    """Raised when a release receipt cannot be made trustworthy."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"could not read JSON object from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReceiptError(f"expected a JSON object in {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _architecture(name: str) -> str:
    lowered = name.lower()
    for architecture in ("arm64", "x64", "x86"):
        if re.search(rf"(?:^|[_-]){architecture}(?:[_.-]|$)", lowered):
            return architecture
    return "unknown"


def _git_value(repo_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _repository_inputs(repo_root: Path) -> dict[str, Any]:
    toolchain = _read_json(repo_root / "toolchain.json")
    vigil_manifest = _read_json(repo_root / "dist" / "scoop" / "vigil.json")
    release_policy = _read_json(repo_root / "release_policy.json")
    try:
        chromium = str(toolchain["chromium"])
        ungoogled_revision = (repo_root / "ungoogled-chromium" / "revision.txt").read_text(
            encoding="utf-8"
        ).strip()
        vigil_revision = (repo_root / "revision.txt").read_text(encoding="utf-8").strip()
        vigil_version = str(vigil_manifest["version"])
    except (KeyError, FileNotFoundError) as exc:
        raise ReceiptError(f"release input is missing: {exc}") from exc
    if not all((chromium, ungoogled_revision, vigil_revision, vigil_version)):
        raise ReceiptError("release input revisions and version must not be empty")
    required_architectures = release_policy.get("release_architectures", [])
    if not isinstance(required_architectures, list) or any(
        architecture not in ARCHITECTURES for architecture in required_architectures
    ):
        raise ReceiptError("release_policy.json contains invalid release_architectures")
    return {
        "chromium": chromium,
        "ungoogled_revision": ungoogled_revision,
        "vigil_revision": vigil_revision,
        "vigil_version": vigil_version,
        "release_architectures": required_architectures,
        "git_revision": _git_value(repo_root, "rev-parse", "HEAD"),
        "git_dirty": bool(_git_value(repo_root, "status", "--porcelain", "--untracked-files=no")),
        "toolchain": toolchain,
    }


def _extension_inputs(repo_root: Path) -> dict[str, Any]:
    sources = _read_json(repo_root / "extension_sources.json")
    ublock = sources.get("ublock_origin")
    if not isinstance(ublock, dict):
        raise ReceiptError("extension_sources.json is missing ublock_origin")
    return {
        "schema_version": sources.get("schema_version"),
        "ublock_origin": {
            key: ublock.get(key)
            for key in ("extension_id", "version", "asset", "url", "sha256")
        },
    }


def _artifact_record(path: Path, artifact_root: Path, release_base_url: str) -> dict[str, Any]:
    suffix = path.suffix.lower()
    return {
        "name": path.name,
        "path": path.relative_to(artifact_root).as_posix(),
        "kind": ARTIFACT_SUFFIXES[suffix],
        "architecture": _architecture(path.name),
        "size": path.stat().st_size,
        "sha256": _sha256(path),
        "release_url": f"{release_base_url.rstrip('/')}/{path.name}",
    }


def collect_artifacts(
    artifact_dir: Path,
    *,
    artifact_paths: Iterable[Path] | None = None,
    release_base_url: str,
) -> list[dict[str, Any]]:
    root = artifact_dir.resolve()
    paths = list(artifact_paths) if artifact_paths is not None else [
        path
        for suffix in ARTIFACT_SUFFIXES
        for path in root.glob(f"*{suffix}")
    ]
    records = []
    seen = set()
    for raw_path in paths:
        path = raw_path.resolve()
        if not path.is_file() or path.suffix.lower() not in ARTIFACT_SUFFIXES:
            continue
        if path in seen:
            continue
        if not path.is_relative_to(root):
            raise ReceiptError(f"artifact is outside artifact directory: {path}")
        seen.add(path)
        records.append(_artifact_record(path, root, release_base_url))
    records.sort(key=lambda record: record["name"].lower())
    if not records:
        raise ReceiptError(f"no EXE, MSI, or ZIP artifacts found in {root}")
    return records


def _manifest_paths(repo_root: Path) -> list[Path]:
    paths = list((repo_root / "dist" / "winget").glob("**/*installer.yaml"))
    paths.extend((repo_root / "dist" / "scoop").glob("*.json"))
    paths.extend((repo_root / "dist" / "chocolatey").glob("**/chocolateyInstall.ps1"))
    return sorted(path for path in paths if path.is_file())


def inspect_manifests(repo_root: Path) -> list[dict[str, Any]]:
    checks = []
    for path in _manifest_paths(repo_root):
        placeholders = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PLACEHOLDER_RE.search(line):
                placeholders.append({"line": line_number, "text": line.strip()})
        checks.append({
            "path": path.relative_to(repo_root).as_posix(),
            "passed": not placeholders,
            "placeholders": placeholders,
        })
    return checks


def _artifact_map(records: list[dict[str, Any]], kind: str) -> dict[str, dict[str, Any]]:
    result = {}
    for record in records:
        if record["kind"] != kind:
            continue
        architecture = record["architecture"]
        if architecture in result:
            raise ReceiptError(f"multiple {kind} artifacts for {architecture}")
        result[architecture] = record
    return result


def _update_winget(path: Path, artifacts: dict[str, dict[str, Any]]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    current = None
    output = []
    for line in lines:
        match = re.match(r"\s*- Architecture:\s*(\S+)", line)
        if match:
            current = match.group(1).lower()
        artifact = artifacts.get(current or "")
        if artifact and re.match(r"\s+InstallerUrl:", line):
            line = re.sub(r"(InstallerUrl:\s*).*$", rf"\g<1>{artifact['release_url']}", line.rstrip("\r\n")) + "\n"
        elif artifact and re.match(r"\s+InstallerSha256:", line):
            line = re.sub(r"(InstallerSha256:\s*).*$", rf"\g<1>{artifact['sha256']}", line.rstrip("\r\n")) + "\n"
        output.append(line)
    path.write_text("".join(output), encoding="utf-8")


def _update_scoop(path: Path, artifacts: dict[str, dict[str, Any]]) -> None:
    data = _read_json(path)
    for architecture, artifact in artifacts.items():
        entry = data.get("architecture", {}).get({"x64": "64bit", "x86": "32bit", "arm64": "arm64"}[architecture])
        if isinstance(entry, dict):
            entry["url"] = artifact["release_url"]
            entry["hash"] = artifact["sha256"]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _replace_assignment(line: str, value: str) -> str:
    prefix = line.split("=", 1)[0]
    quote = "'" if "'" in line else '"'
    return f"{prefix}= {quote}{value}{quote}\n"


def _update_chocolatey(path: Path, artifacts: dict[str, dict[str, Any]]) -> None:
    x86 = artifacts.get("x86")
    x64 = artifacts.get("x64")
    output = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        if x86 and re.match(r"\s*url\s*=", line):
            line = _replace_assignment(line, x86["release_url"])
        elif x64 and re.match(r"\s*url64bit\s*=", line):
            line = _replace_assignment(line, x64["release_url"])
        elif x86 and re.match(r"\s*checksum\s*=", line):
            line = _replace_assignment(line, x86["sha256"])
        elif x64 and re.match(r"\s*checksum64\s*=", line):
            line = _replace_assignment(line, x64["sha256"])
        output.append(line)
    path.write_text("".join(output), encoding="utf-8")


def update_manifests(repo_root: Path, records: list[dict[str, Any]]) -> None:
    """Fill package-manager hashes/URLs for artifacts that are present."""

    installers = _artifact_map(records, "installer")
    archives = _artifact_map(records, "archive")
    for path in _manifest_paths(repo_root):
        if path.name.endswith("installer.yaml"):
            _update_winget(path, installers)
        elif path.parent.name == "scoop":
            _update_scoop(path, archives)
        elif path.name == "chocolateyInstall.ps1":
            _update_chocolatey(path, installers)


def generate_receipt(
    repo_root: Path,
    *,
    artifact_dir: Path,
    output: Path | None = None,
    artifact_paths: Iterable[Path] | None = None,
    strict_manifests: bool = False,
    update_package_manifests: bool = False,
    release_base_url: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    artifact_dir = artifact_dir.resolve()
    inputs = _repository_inputs(repo_root)
    release_base_url = release_base_url or (
        "https://github.com/SysAdminDoc/Vigil/releases/download/"
        f"v{inputs['vigil_version']}"
    )
    if not release_base_url.startswith("https://"):
        raise ReceiptError("release base URL must use HTTPS")
    records = collect_artifacts(
        artifact_dir,
        artifact_paths=artifact_paths,
        release_base_url=release_base_url,
    )
    if update_package_manifests:
        update_manifests(repo_root, records)
    manifest_checks = inspect_manifests(repo_root)
    manifests_passed = all(check["passed"] for check in manifest_checks)
    insecure_downloads = os.environ.get("VIGIL_SSL_VERIFICATION_DISABLED") == "1"
    installer_architectures = set(_artifact_map(records, "installer"))
    archive_architectures = set(_artifact_map(records, "archive"))
    required_architectures = set(inputs["release_architectures"])
    missing_architectures = sorted(
        (required_architectures - installer_architectures)
        | (required_architectures - archive_architectures)
    )
    artifact_contract_passed = not missing_architectures
    report = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": "pass" if (
            not strict_manifests
            or (manifests_passed and artifact_contract_passed and not insecure_downloads)
        ) else "fail",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "signing": {"status": "unsigned", "required": False},
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "ssl_verification_disabled": insecure_downloads,
        },
        "source": inputs,
        "extensions": _extension_inputs(repo_root),
        "release_base_url": release_base_url,
        "artifacts": records,
        "artifact_contract": {
            "required_architectures": sorted(required_architectures),
            "installer_architectures": sorted(installer_architectures),
            "archive_architectures": sorted(archive_architectures),
            "missing_architectures": missing_architectures,
            "passed": artifact_contract_passed,
        },
        "package_manifest_check": {
            "strict": strict_manifests,
            "passed": manifests_passed,
            "manifests": manifest_checks,
        },
        "release_safety": {
            "insecure_downloads": {
                "enabled": insecure_downloads,
                "passed": not insecure_downloads,
            },
        },
    }
    if output:
        output = output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, output)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--artifact-dir", type=Path, default=Path("build"))
    parser.add_argument("--artifact", action="append", type=Path, dest="artifacts")
    parser.add_argument("--output", type=Path, default=Path("build/release-receipt.json"))
    parser.add_argument("--strict-manifests", action="store_true")
    parser.add_argument("--update-manifests", action="store_true")
    parser.add_argument("--release-base-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = generate_receipt(
            args.repo_root,
            artifact_dir=args.artifact_dir,
            output=args.output,
            artifact_paths=args.artifacts,
            strict_manifests=args.strict_manifests,
            update_package_manifests=args.update_manifests,
            release_base_url=args.release_base_url,
        )
    except (OSError, ReceiptError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
