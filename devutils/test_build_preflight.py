import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from devutils import build_preflight
from tools.atomic_stage import atomic_copy_file, atomic_copy_tree


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def seed_preflight_repo(tmp_path):
    archive = b"pinned uBlock archive"
    cache = tmp_path / "build" / "download_cache"
    cache.mkdir(parents=True)
    (cache / "uBlock0_1.72.2.chromium.zip").write_bytes(archive)
    write_json(
        tmp_path / "extension_sources.json",
        {
            "ublock_origin": {
                "asset": "uBlock0_1.72.2.chromium.zip",
                "sha256": hashlib.sha256(archive).hexdigest(),
            }
        },
    )
    (tmp_path / "build" / "src").mkdir(parents=True)
    (tmp_path / "build" / "src" / "BUILD.gn").write_text("# seeded\n", encoding="utf-8")
    return cache


def test_incremental_preflight_verifies_pinned_archive_and_source(tmp_path):
    cache = seed_preflight_repo(tmp_path)

    report = build_preflight.run_preflight(tmp_path, cache_dir=cache)

    assert report["passed"] is True
    assert {check["id"] for check in report["checks"]} == {
        "download_cache",
        "ublock_archive",
        "incremental_source_tree",
    }

    (cache / "uBlock0_1.72.2.chromium.zip").write_bytes(b"tampered")
    failed = build_preflight.run_preflight(tmp_path, cache_dir=cache)
    assert failed["passed"] is False
    assert failed["checks"][1]["detail"] == (
        "sha256 mismatch for "
        f"{cache / 'uBlock0_1.72.2.chromium.zip'}"
    )


def test_fresh_preflight_rejects_partial_download_before_hash_check(tmp_path, monkeypatch):
    cache = seed_preflight_repo(tmp_path)
    (tmp_path / "ungoogled-chromium").mkdir()
    (tmp_path / "ungoogled-chromium" / "downloads.ini").write_text(
        "[chromium]\n", encoding="utf-8"
    )
    required = cache / "chromium.tar.xz"
    required.with_name(required.name + ".partial").write_bytes(b"incomplete")
    monkeypatch.setattr(
        build_preflight,
        "_download_requirements",
        lambda repo_root, cache_dir: [{"name": "chromium", "path": required, "hashes": {}}],
    )
    hash_checked = False

    def fail_if_hashes_are_checked(repo_root, cache_dir):
        nonlocal hash_checked
        hash_checked = True
        return None

    monkeypatch.setattr(build_preflight, "_check_download_hashes", fail_if_hashes_are_checked)

    report = build_preflight.run_preflight(
        tmp_path,
        cache_dir=cache,
        mode="fresh-tarball",
    )

    assert report["passed"] is False
    assert report["checks"][-1]["id"] == "download_hashes"
    assert report["checks"][-1]["passed"] is False
    assert hash_checked is False


def test_package_preflight_is_fail_closed_before_output_staging(tmp_path):
    cache = seed_preflight_repo(tmp_path)
    build_out = tmp_path / "build" / "src" / "out" / "Default"
    build_out.mkdir(parents=True)
    (build_out / "args.gn").write_text("target_cpu = \"x64\"\n", encoding="utf-8")
    (build_out / "mini_installer.exe").write_bytes(b"installer")
    (tmp_path / "build" / "src" / "chrome" / "tools" / "build" / "win").mkdir(parents=True)
    (tmp_path / "build" / "src" / "chrome" / "tools" / "build" / "win" / "FILES.cfg").write_text(
        "", encoding="utf-8"
    )
    (tmp_path / "initial_preferences").write_text("{}", encoding="utf-8")
    for extension in ("ntp-extension", "palette-extension"):
        locale = tmp_path / extension / "_locales" / "en"
        locale.mkdir(parents=True)
        (tmp_path / extension / "manifest.json").write_text("{}", encoding="utf-8")
        (locale / "messages.json").write_text("{}", encoding="utf-8")

    report = build_preflight.assert_package_ready(tmp_path, build_out, offline=True)
    assert report["passed"] is True
    assert (cache / "uBlock0_1.72.2.chromium.zip").is_file()

    (tmp_path / "initial_preferences").unlink()
    with pytest.raises(build_preflight.PreflightError, match="initial_preferences"):
        build_preflight.assert_package_ready(tmp_path, build_out, offline=True)


def test_atomic_copy_file_promotes_complete_content(tmp_path):
    source = tmp_path / "source.bin"
    target = tmp_path / "nested" / "target.bin"
    source.write_bytes(b"complete payload")

    atomic_copy_file(source, target)

    assert target.read_bytes() == b"complete payload"
    assert not list(target.parent.glob(f".{target.name}.stage-*"))


def test_atomic_copy_tree_recovers_stale_backup_then_replaces_target(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "new.txt").write_text("new", encoding="utf-8")
    target = tmp_path / "target"
    stale_backup = tmp_path / ".target.previous"
    stale_backup.mkdir()
    (stale_backup / "old.txt").write_text("old", encoding="utf-8")

    atomic_copy_tree(source, target)

    assert (target / "new.txt").read_text(encoding="utf-8") == "new"
    assert not (target / "old.txt").exists()
    assert not stale_backup.exists()
    assert not list(tmp_path.glob(".target.stage-*"))


def test_atomic_copy_tree_keeps_existing_target_when_copy_fails(tmp_path):
    source = tmp_path / "missing-source"
    target = tmp_path / "target"
    target.mkdir()
    (target / "old.txt").write_text("old", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        atomic_copy_tree(source, target)

    assert (target / "old.txt").read_text(encoding="utf-8") == "old"
    assert not (tmp_path / ".target.previous").exists()


def test_ssl_bypass_requires_explicit_development_environment():
    result = subprocess.run(
        [sys.executable, "build.py", "--ci", "--disable-ssl-verification"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 2
    assert "development-only" in result.stderr
