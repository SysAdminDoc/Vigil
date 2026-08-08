#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage the pinned uBlock Origin Chromium build into a Vigil artifact.

The archive is resolved in this order:

1. An explicitly supplied archive.
2. The verified build download cache.
3. The exact HTTPS release URL in ``extension_sources.json``.

``--offline`` stops before any network request and is used by release jobs to
prove that the cache was seeded and verified before packaging. The archive is
validated, extracted into a temporary sibling directory, and promoted only
after its manifest and every member path pass validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = REPO_ROOT / "extension_sources.json"
DEFAULT_BUILD_OUT = REPO_ROOT / "build" / "src" / "out" / "Default"
DEFAULT_CACHE_DIR = REPO_ROOT / "build" / "download_cache"
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"required JSON file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"expected a JSON object in {path}")
    return value


def load_source(config_path: Path = DEFAULT_CONFIG) -> dict[str, str]:
    """Load and validate the immutable uBlock release descriptor."""

    config = _read_json(config_path)
    if config.get("schema_version") != 1:
        raise RuntimeError(f"unsupported extension source schema in {config_path}")
    source = config.get("ublock_origin")
    if not isinstance(source, dict):
        raise RuntimeError(f"ublock_origin is missing from {config_path}")
    required = ("extension_id", "version", "asset", "url", "sha256")
    if any(not isinstance(source.get(key), str) or not source[key] for key in required):
        raise RuntimeError(f"incomplete uBlock source descriptor in {config_path}")
    if not source["url"].startswith("https://"):
        raise RuntimeError("uBlock source URL must use HTTPS")
    digest = source["sha256"].lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise RuntimeError("uBlock source sha256 must be a 64-character hex digest")
    if source["asset"] not in source["url"]:
        raise RuntimeError("uBlock asset name must be present in its release URL")
    return {**source, "sha256": digest}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_archive(path: Path, source: dict[str, str]) -> None:
    if not path.is_file():
        raise RuntimeError(f"uBlock archive is missing: {path}")
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise RuntimeError(
            f"uBlock archive is unexpectedly large ({path.stat().st_size} bytes)"
        )
    actual = _sha256(path)
    if actual != source["sha256"]:
        raise RuntimeError(
            f"uBlock archive hash mismatch for {path}: expected "
            f"{source['sha256']}, got {actual}"
        )


def _download_archive(source: dict[str, str], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.part")
    if temporary.exists():
        temporary.unlink()
    request = urllib.request.Request(
        source["url"], headers={"User-Agent": "Vigil-Browser-Builder"}
    )
    total = 0
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            with temporary.open("wb") as stream:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise RuntimeError("uBlock download exceeded the archive size limit")
                    stream.write(chunk)
        _verify_archive(temporary, source)
        os.replace(temporary, destination)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    print(f"  Cached verified uBlock archive: {destination}")
    return destination


def resolve_archive(
    source: dict[str, str],
    *,
    repo_root: Path = REPO_ROOT,
    cache_dir: Path | None = None,
    archive_path: Path | None = None,
    offline: bool = False,
) -> Path:
    """Resolve a verified archive without consulting a mutable release API."""

    if archive_path is not None:
        archive = archive_path.resolve()
        _verify_archive(archive, source)
        return archive

    cache = cache_dir or repo_root / "build" / "download_cache"
    cached = cache / source["asset"]
    if cached.exists():
        _verify_archive(cached, source)
        print(f"  Using verified cached uBlock archive: {cached}")
        return cached
    if offline:
        raise RuntimeError(
            f"offline mode requires a verified archive at {cached}; "
            "seed the build cache before packaging"
        )
    return _download_archive(source, cached)


def _normalized_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or "\x00" in normalized or path.is_absolute():
        raise RuntimeError(f"unsafe uBlock archive member path: {name!r}")
    if any(part in ("", ".", "..") for part in path.parts):
        raise RuntimeError(f"unsafe uBlock archive member path: {name!r}")
    return "/".join(path.parts)


def _validate_members(zf: zipfile.ZipFile) -> tuple[str, dict[str, str]]:
    """Validate ZIP members and return the single optional root prefix."""

    members: dict[str, str] = {}
    total_uncompressed = 0
    for info in zf.infolist():
        normalized = _normalized_member_name(info.filename.rstrip("/"))
        if not normalized:
            continue
        mode = (info.external_attr >> 16) & 0o170000
        if mode == stat.S_IFLNK:
            raise RuntimeError(f"symbolic links are not allowed in uBlock archive: {info.filename}")
        if info.file_size > MAX_UNCOMPRESSED_BYTES:
            raise RuntimeError(f"uBlock archive member is too large: {info.filename}")
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
            raise RuntimeError("uBlock archive exceeds the uncompressed size limit")
        if normalized in members:
            raise RuntimeError(f"duplicate uBlock archive member: {info.filename}")
        members[normalized] = info.filename

    manifest_names = [name for name in members if name == "manifest.json" or name.endswith("/manifest.json")]
    if len(manifest_names) != 1:
        raise RuntimeError("uBlock archive must contain exactly one manifest.json")
    manifest_name = manifest_names[0]
    prefix = manifest_name[:-len("manifest.json")]
    if prefix and not prefix.endswith("/"):
        raise RuntimeError("invalid uBlock archive manifest prefix")
    if any(not name.startswith(prefix) for name in members):
        raise RuntimeError("uBlock archive contains files outside its extension root")
    return prefix, members


def _safe_target(root: Path, relative_name: str) -> Path:
    target = (root / Path(*PurePosixPath(relative_name).parts)).resolve()
    if not target.is_relative_to(root.resolve()):
        raise RuntimeError(f"uBlock archive member escapes staging root: {relative_name}")
    return target


def _extract_archive(archive: Path, source: dict[str, str], stage: Path) -> str:
    try:
        zf = zipfile.ZipFile(archive)
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"invalid uBlock archive: {archive}") from exc
    with zf:
        prefix, members = _validate_members(zf)
        manifest_name = f"{prefix}manifest.json"
        try:
            manifest = json.loads(zf.read(members[manifest_name]).decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("uBlock manifest is missing or invalid") from exc
        actual_version = manifest.get("version")
        if actual_version != source["version"]:
            raise RuntimeError(
                f"uBlock manifest version {actual_version!r} does not match pinned "
                f"version {source['version']!r}"
            )

        for normalized, archive_name in members.items():
            if not normalized.startswith(prefix):
                raise RuntimeError(f"uBlock archive member is outside its root: {archive_name}")
            relative_name = normalized[len(prefix):]
            if not relative_name:
                continue
            if archive_name.endswith(("/", "\\")):
                continue
            target = _safe_target(stage, relative_name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(archive_name) as source_stream, target.open("wb") as output:
                shutil.copyfileobj(source_stream, output, length=1024 * 1024)
    return actual_version


def _write_pointer(build_out: Path, version: str) -> None:
    pointer_dir = build_out / "default_extensions"
    pointer_dir.mkdir(parents=True, exist_ok=True)
    pointer = pointer_dir / f"{UBLOCK_EXTENSION_ID}.json"
    temporary = pointer.with_name(f".{pointer.name}.tmp")
    temporary.write_text(
        json.dumps(
            {
                "external_crx": f"Extensions/{UBLOCK_EXTENSION_ID}/{version}",
                "external_version": version,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, pointer)


UBLOCK_EXTENSION_ID = "cjpalhdlnbpafiamejdnhcphjbkeiagm"


def install_ublock(
    chrome_dir: Path,
    *,
    repo_root: Path = REPO_ROOT,
    config_path: Path = DEFAULT_CONFIG,
    cache_dir: Path | None = None,
    archive_path: Path | None = None,
    offline: bool = False,
) -> Path:
    """Verify and stage uBlock, returning the final extension directory."""

    source = load_source(config_path)
    if source["extension_id"] != UBLOCK_EXTENSION_ID:
        raise RuntimeError("extension_sources.json contains an unexpected uBlock ID")
    archive = resolve_archive(
        source,
        repo_root=repo_root,
        cache_dir=cache_dir,
        archive_path=archive_path,
        offline=offline,
    )
    extensions_root = chrome_dir / "Extensions" / UBLOCK_EXTENSION_ID
    extensions_root.mkdir(parents=True, exist_ok=True)
    target = extensions_root / source["version"]
    stage = Path(tempfile.mkdtemp(prefix=f".{source['version']}.stage-", dir=extensions_root))
    backup = extensions_root / f".{source['version']}.previous"
    try:
        actual_version = _extract_archive(archive, source, stage)
        if backup.exists():
            raise RuntimeError(f"refusing to overwrite stale uBlock backup: {backup}")
        if target.exists():
            target.rename(backup)
        try:
            stage.rename(target)
        except Exception:
            if backup.exists() and not target.exists():
                backup.rename(target)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    _write_pointer(chrome_dir, actual_version)
    print(f"  uBlock Origin {actual_version} installed successfully")
    return target


def download_and_extract_ublock(chrome_dir: Path) -> bool:
    """Compatibility wrapper for existing local build scripts."""

    try:
        install_ublock(chrome_dir)
    except (OSError, RuntimeError, urllib.error.URLError, zipfile.BadZipFile) as exc:
        print(f"  ERROR: {exc}")
        return False
    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-out", type=Path, default=DEFAULT_BUILD_OUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--archive", type=Path, help="Use a specific verified local archive")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Refuse all network access and require the verified cache/archive",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.build_out.exists():
        print(f"ERROR: build output directory not found: {args.build_out}", file=sys.stderr)
        return 2
    try:
        install_ublock(
            args.build_out,
            repo_root=REPO_ROOT,
            config_path=args.config,
            cache_dir=args.cache_dir,
            archive_path=args.archive,
            offline=args.offline,
        )
    except (OSError, RuntimeError, urllib.error.URLError, zipfile.BadZipFile) as exc:
        print(f"ERROR: uBlock setup failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
