import zipfile
from pathlib import Path

import pytest

from package import (
    _create_archive_atomically,
    _filescfg_cpu_arch,
    _normalize_cpu_arch,
)
from devutils.smoke_test import find_extracted_build_root


@pytest.mark.parametrize(
    ("requested", "target", "expected"),
    [
        ("auto", "x64", "x64"),
        ("x64", "x64", "x64"),
        ("64bit", "x64", "x64"),
        ("x86", "x86", "x86"),
        ("32bit", "x86", "x86"),
        ("arm64", "arm64", "arm64"),
        ("arm", "arm64", "arm64"),
    ],
)
def test_normalize_cpu_arch_accepts_target_aliases(requested, target, expected):
    assert _normalize_cpu_arch(requested, target) == expected


def test_normalize_cpu_arch_rejects_mismatched_target():
    with pytest.raises(RuntimeError, match="Package target mismatch"):
        _normalize_cpu_arch("x86", "x64")


def test_filescfg_uses_chromium_legacy_architecture_names():
    assert _filescfg_cpu_arch("x64") == "64bit"
    assert _filescfg_cpu_arch("x86") == "32bit"
    assert _filescfg_cpu_arch("arm64") == "arm"


def test_archive_staging_preserves_the_published_archive_root(tmp_path):
    build_outputs = tmp_path / "out"
    build_outputs.mkdir()
    (build_outputs / "chrome.exe").write_bytes(b"portable")
    output = tmp_path / "vigil-portable.zip"

    _create_archive_atomically((Path("chrome.exe"),), build_outputs, output)

    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == ["vigil-portable/chrome.exe"]
    assert not list(tmp_path.glob(".vigil-portable.stage-*"))


def test_smoke_harness_resolves_named_portable_archive_root(tmp_path):
    extract_dir = tmp_path / "extract"
    named_root = extract_dir / "vigil-portable"
    named_root.mkdir(parents=True)
    (named_root / "chrome.exe").write_bytes(b"portable")

    assert find_extracted_build_root(extract_dir) == named_root
