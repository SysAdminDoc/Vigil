import hashlib
import json

from devutils.release_receipt import generate_receipt


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def seed_repo(tmp_path, architectures=("x64",)):
    write_json(tmp_path / "toolchain.json", {"chromium": "149.0.1.2", "clang": "test"})
    write_json(
        tmp_path / "release_policy.json",
        {"release_architectures": ["x64", "x86", "arm64"]},
    )
    (tmp_path / "revision.txt").write_text("7\n", encoding="utf-8")
    (tmp_path / "ungoogled-chromium").mkdir()
    (tmp_path / "ungoogled-chromium" / "revision.txt").write_text("3\n", encoding="utf-8")
    write_json(
        tmp_path / "dist" / "scoop" / "vigil.json",
        {
            "version": "0.2.1",
            "architecture": {
                "64bit": {"url": "old", "hash": "0" * 64},
                "32bit": {"url": "old", "hash": "0" * 64},
                "arm64": {"url": "old", "hash": "0" * 64},
            },
        },
    )
    winget = tmp_path / "dist" / "winget" / "SysAdminDoc.Vigil" / "0.2.1"
    winget.mkdir(parents=True)
    winget.joinpath("SysAdminDoc.Vigil.installer.yaml").write_text(
        "\n".join(
            [
                "Installers:",
                *sum(
                    [
                        [
                            f"  - Architecture: {architecture}",
                            "    InstallerUrl: old",
                            "    InstallerSha256: TODO_FILL_BEFORE_PR",
                        ]
                        for architecture in architectures
                    ],
                    [],
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    chocolatey = tmp_path / "dist" / "chocolatey" / "vigil" / "tools"
    chocolatey.mkdir(parents=True)
    chocolatey.joinpath("chocolateyInstall.ps1").write_text(
        "\n".join(
            [
                "  url            = 'old-x86'",
                "  url64bit       = 'old-x64'",
                f"  checksum       = '{'0' * 64}'",
                f"  checksum64     = '{'0' * 64}'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        tmp_path / "extension_sources.json",
        {
            "schema_version": 1,
            "ublock_origin": {
                "extension_id": "cjpalhdlnbpafiamejdnhcphjbkeiagm",
                "version": "1.72.2",
                "asset": "uBlock.zip",
                "url": "https://example.test/uBlock.zip",
                "sha256": "a" * 64,
            },
        },
    )
    build = tmp_path / "build"
    build.mkdir()
    for architecture in architectures:
        (build / f"vigil_installer_{architecture}.exe").write_bytes(
            f"exe-{architecture}".encode()
        )
        (build / f"vigil_windows_{architecture}.zip").write_bytes(
            f"zip-{architecture}".encode()
        )
    return build


def test_receipt_hashes_artifacts_and_reports_unsigned_status(tmp_path):
    build = seed_repo(tmp_path)
    receipt_path = build / "receipt.json"

    report = generate_receipt(tmp_path, artifact_dir=build, output=receipt_path)

    assert report["status"] == "pass"
    assert report["signing"] == {"status": "unsigned", "required": False}
    artifact = next(item for item in report["artifacts"] if item["name"].endswith("x64.exe"))
    assert artifact["sha256"] == hashlib.sha256(
        (build / artifact["name"]).read_bytes()
    ).hexdigest().upper()
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["schema_version"] == 1
    assert report["package_manifest_check"]["passed"] is False


def test_strict_receipt_fails_placeholders_then_updates_all_manifests(tmp_path):
    build = seed_repo(tmp_path, architectures=("x64", "x86", "arm64"))

    report = generate_receipt(
        tmp_path,
        artifact_dir=build,
        strict_manifests=True,
        update_package_manifests=True,
        release_base_url="https://example.test/releases/v0.2.1",
    )

    assert report["status"] == "pass"
    assert report["package_manifest_check"]["passed"] is True
    assert "TODO_FILL_BEFORE_PR" not in (
        tmp_path / "dist" / "winget" / "SysAdminDoc.Vigil" / "0.2.1" / "SysAdminDoc.Vigil.installer.yaml"
    ).read_text(encoding="utf-8")
    assert "0" * 64 not in (tmp_path / "dist" / "scoop" / "vigil.json").read_text(
        encoding="utf-8"
    )
    assert "0" * 64 not in (
        tmp_path / "dist" / "chocolatey" / "vigil" / "tools" / "chocolateyInstall.ps1"
    ).read_text(encoding="utf-8")


def test_strict_receipt_reports_missing_architecture(tmp_path):
    build = seed_repo(tmp_path, architectures=("x64",))

    report = generate_receipt(tmp_path, artifact_dir=build, strict_manifests=True)

    assert report["status"] == "fail"
    assert report["artifact_contract"]["missing_architectures"] == ["arm64", "x86"]
