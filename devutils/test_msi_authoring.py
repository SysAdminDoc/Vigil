from pathlib import Path


WXS_PATH = Path(__file__).resolve().parent.parent / "installer" / "vigil.wxs"


def test_per_machine_msi_uses_machine_owned_component_key_path():
    source = WXS_PATH.read_text(encoding="utf-8")

    assert 'Scope="perMachine"' in source
    assert 'Root="HKLM"' in source
    assert 'Root="HKCU"' not in source
    assert 'UpgradeCode="{3F7B1D1E-85E6-4F6F-8CB8-73F0AA4CBF1A}"' in source
    assert "<MajorUpgrade" in source


def test_msi_authors_all_build_output_files_and_start_menu_shortcut():
    source = WXS_PATH.read_text(encoding="utf-8")

    assert '<Files Include="$(var.BuildOutput)\\**" />' in source
    assert 'Target="[INSTALLFOLDER]chrome.exe"' in source
    assert 'RemoveFolder Id="RemoveVigilStartMenuFolder" On="uninstall"' in source
