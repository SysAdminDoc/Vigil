import pytest

from package import _filescfg_cpu_arch, _normalize_cpu_arch


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
