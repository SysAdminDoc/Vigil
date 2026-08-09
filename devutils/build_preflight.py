#!/usr/bin/env python3
"""Fail-closed, offline-safe input checks for build and package recovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
UBLOCK_ASSET = "uBlock0_1.72.2.chromium.zip"


class PreflightError(RuntimeError):
    """Raised when a required build input cannot be verified."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def _load_download_info(repo_root: Path):
    utils = repo_root / "ungoogled-chromium" / "utils"
    sys.path.insert(0, str(utils))
    try:
        import downloads
    finally:
        sys.path.pop(0)
    paths = [repo_root / "ungoogled-chromium" / "downloads.ini", repo_root / "downloads.ini"]
    return downloads.DownloadInfo(paths)


def _download_requirements(repo_root: Path, cache_dir: Path) -> list[dict[str, Any]]:
    info = _load_download_info(repo_root)
    requirements = []
    for name, properties in info.properties_iter():
        requirements.append({
            "name": name,
            "path": cache_dir / properties.download_filename,
            "hashes": properties.hashes,
        })
        if properties.has_hash_url():
            _, hash_filename, _ = properties.hashes["hash_url"]
            requirements.append({
                "name": f"{name} hash list",
                "path": cache_dir / hash_filename,
                "hashes": {},
            })
    return requirements


def _check_download_hashes(repo_root: Path, cache_dir: Path) -> str | None:
    try:
        info = _load_download_info(repo_root)
        sys.path.insert(0, str(repo_root / "ungoogled-chromium" / "utils"))
        try:
            import downloads

            downloads.check_downloads(info, cache_dir, None)
        finally:
            sys.path.pop(0)
    except BaseException as exc:  # upstream HashMismatchError inherits BaseException
        return str(exc) or exc.__class__.__name__
    return None


def _check_ublock(cache_dir: Path, repo_root: Path) -> str | None:
    try:
        source = json.loads((repo_root / "extension_sources.json").read_text(encoding="utf-8"))[
            "ublock_origin"
        ]
        archive = cache_dir / source["asset"]
        if not archive.is_file():
            return f"missing {archive}"
        if _sha256(archive) != source["sha256"].lower():
            return f"sha256 mismatch for {archive}"
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return str(exc)
    return None


def _check_path(checks: list[dict[str, Any]], label: str, path: Path) -> None:
    checks.append({"id": label, "path": str(path), "passed": path.exists()})


def run_preflight(
    repo_root: Path = ROOT,
    *,
    cache_dir: Path | None = None,
    build_out: Path | None = None,
    mode: str = "incremental",
) -> dict[str, Any]:
    """Inspect required inputs without creating or mutating build files."""

    repo_root = Path(repo_root).resolve()
    cache_dir = (cache_dir or repo_root / "build" / "download_cache").resolve()
    build_out = (build_out or repo_root / "build" / "src" / "out" / "Default").resolve()
    if mode not in {"incremental", "fresh-tarball"}:
        raise PreflightError(f"unsupported preflight mode: {mode}")

    checks: list[dict[str, Any]] = []
    cache_dir_exists = cache_dir.is_dir()
    checks.append({"id": "download_cache", "path": str(cache_dir), "passed": cache_dir_exists})
    ublock_error = _check_ublock(cache_dir, repo_root) if cache_dir_exists else "cache is missing"
    checks.append({"id": "ublock_archive", "path": str(cache_dir / UBLOCK_ASSET), "passed": not ublock_error, "detail": ublock_error})

    if mode == "fresh-tarball":
        requirements = _download_requirements(repo_root, cache_dir)
        for requirement in requirements:
            path = requirement["path"]
            partial = path.with_name(f"{path.name}.partial")
            passed = path.is_file() and not partial.exists()
            checks.append({
                "id": "download_input",
                "name": requirement["name"],
                "path": str(path),
                "passed": passed,
                "detail": "unfinished .partial file exists" if partial.exists() else "",
            })
        hash_error = _check_download_hashes(repo_root, cache_dir) if all(
            check["passed"] for check in checks if check["id"] == "download_input"
        ) else "one or more download inputs are missing"
        checks.append({"id": "download_hashes", "passed": hash_error is None, "detail": hash_error})
        if not (repo_root / "ungoogled-chromium" / "downloads.ini").is_file():
            raise PreflightError("ungoogled-chromium/downloads.ini is missing")
    else:
        _check_path(checks, "incremental_source_tree", repo_root / "build" / "src" / "BUILD.gn")

    report = {
        "schema_version": 1,
        "mode": mode,
        "cache_dir": str(cache_dir),
        "build_out": str(build_out),
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
        "network": "not used",
    }
    return report


def assert_package_ready(repo_root: Path, build_out: Path, *, offline: bool) -> dict[str, Any]:
    """Validate package inputs before any output or staged tree is mutated."""

    repo_root = Path(repo_root).resolve()
    build_out = Path(build_out).resolve()
    required = (
        build_out / "args.gn",
        build_out / "mini_installer.exe",
        repo_root / "build" / "src" / "chrome" / "tools" / "build" / "win" / "FILES.cfg",
        repo_root / "initial_preferences",
        repo_root / "ntp-extension" / "manifest.json",
        repo_root / "ntp-extension" / "_locales" / "en" / "messages.json",
        repo_root / "palette-extension" / "manifest.json",
        repo_root / "palette-extension" / "_locales" / "en" / "messages.json",
    )
    missing = [str(path) for path in required if not path.is_file()]
    checks = [{"id": "package_input", "path": path, "passed": path not in missing} for path in map(str, required)]
    if offline:
        cache = repo_root / "build" / "download_cache"
        ublock_error = _check_ublock(cache, repo_root)
        checks.append({"id": "offline_ublock_cache", "path": str(cache / UBLOCK_ASSET), "passed": not ublock_error, "detail": ublock_error})
    report = {"schema_version": 1, "checks": checks, "passed": all(check["passed"] for check in checks), "network": "not used"}
    if not report["passed"]:
        details = "; ".join(check["path"] for check in checks if not check["passed"])
        raise PreflightError(f"package preflight failed: {details}")
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--build-out", type=Path)
    parser.add_argument("--mode", choices=("incremental", "fresh-tarball"), default="incremental")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = run_preflight(
            args.repo_root,
            cache_dir=args.cache_dir,
            build_out=args.build_out,
            mode=args.mode,
        )
    except (OSError, PreflightError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for check in report["checks"]:
            print(f"{'PASS' if check['passed'] else 'FAIL':4} {check['id']} {check.get('path', '')}")
        print(f"\nBuild preflight: {'PASS' if report['passed'] else 'FAIL'}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
