import hashlib
import json
import zipfile

import pytest

from setup_extensions import install_ublock


def write_archive(path, version="1.72.2", members=None):
    members = members or {
        "manifest.json": json.dumps({"manifest_version": 2, "version": version}),
        "js/background.js": "self.addEventListener('install', () => {});",
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def write_config(path, archive, version="1.72.2"):
    write = {
        "schema_version": 1,
        "ublock_origin": {
            "extension_id": "cjpalhdlnbpafiamejdnhcphjbkeiagm",
            "version": version,
            "asset": archive.name,
            "url": f"https://example.test/{archive.name}",
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        },
    }
    path.write_text(json.dumps(write), encoding="utf-8")


def test_install_ublock_uses_verified_archive_and_writes_pointer(tmp_path):
    archive = tmp_path / "uBlock0_1.72.2.chromium.zip"
    config = tmp_path / "extension_sources.json"
    build_out = tmp_path / "out"
    build_out.mkdir()
    write_archive(archive)
    write_config(config, archive)

    target = install_ublock(
        build_out,
        repo_root=tmp_path,
        config_path=config,
        archive_path=archive,
        offline=True,
    )

    assert (target / "manifest.json").is_file()
    pointer = build_out / "default_extensions" / "cjpalhdlnbpafiamejdnhcphjbkeiagm.json"
    assert json.loads(pointer.read_text(encoding="utf-8")) == {
        "external_crx": "Extensions/cjpalhdlnbpafiamejdnhcphjbkeiagm/1.72.2",
        "external_version": "1.72.2",
    }


def test_install_ublock_rejects_traversal_before_replacing_existing_target(tmp_path):
    archive = tmp_path / "uBlock0_1.72.2.chromium.zip"
    config = tmp_path / "extension_sources.json"
    build_out = tmp_path / "out"
    target = build_out / "Extensions" / "cjpalhdlnbpafiamejdnhcphjbkeiagm" / "1.72.2"
    target.mkdir(parents=True)
    sentinel = target / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    write_archive(
        archive,
        members={
            "manifest.json": json.dumps({"manifest_version": 2, "version": "1.72.2"}),
            "../escape.txt": "must not be extracted",
        },
    )
    write_config(config, archive)

    with pytest.raises(RuntimeError, match="unsafe.*path"):
        install_ublock(
            build_out,
            repo_root=tmp_path,
            config_path=config,
            archive_path=archive,
            offline=True,
        )

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_install_ublock_offline_requires_cache(tmp_path):
    archive = tmp_path / "uBlock0_1.72.2.chromium.zip"
    config = tmp_path / "extension_sources.json"
    build_out = tmp_path / "out"
    build_out.mkdir()
    write_archive(archive)
    write_config(config, archive)
    archive.unlink()

    with pytest.raises(RuntimeError, match="offline mode requires"):
        install_ublock(
            build_out,
            repo_root=tmp_path,
            config_path=config,
            cache_dir=tmp_path / "cache",
            offline=True,
        )
