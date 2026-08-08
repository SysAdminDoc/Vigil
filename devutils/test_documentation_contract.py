import json
import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
VERSION_SOURCE = ROOT / "dist" / "scoop" / "vigil.json"
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def read(path):
    return path.read_text(encoding="utf-8")


def test_release_version_and_chromium_target_have_one_checked_source():
    version = json.loads(read(VERSION_SOURCE))["version"]
    toolchain = json.loads(read(ROOT / "toolchain.json"))
    readme = read(ROOT / "README.md")
    changelog = read(ROOT / "CHANGELOG.md")

    assert f"badge/version-{version}-blue" in readme
    assert f"## [Unreleased] &mdash; v{version}" in changelog
    assert f"`{toolchain['chromium']}`" in readme
    for extension in ("ntp-extension", "palette-extension"):
        manifest = json.loads(read(ROOT / extension / "manifest.json"))
        assert manifest["version"] == version


def test_readme_documents_the_executable_release_contract():
    readme = read(ROOT / "README.md")

    for command in (
        "python build.py",
        "python package.py",
        "python package.py --offline",
        "python -m pytest -q",
        "python -m ruff check .",
        "python devutils/privacy_probe.py",
        "python devutils/smoke_test.py --build-out build/src/out/Default",
    ):
        assert command in readme
    for artifact in (
        "ungoogled-chromium_*_installer_*.exe",
        "vigil_*_installer_*.msi",
        "ungoogled-chromium_*_windows_*.zip",
        "build/release-receipt.json",
    ):
        assert artifact in readme


def test_existing_architecture_docs_have_live_workflow_and_design_links():
    candidates = [
        ROOT / "docs" / "ARCHITECTURE.md",
        ROOT / "docs" / "ROADMAP_PROGRESS.md",
    ]
    existing = [path for path in candidates if path.is_file()]
    for path in existing:
        source = read(path)
        for match in MARKDOWN_LINK.finditer(source):
            target = unquote(match.group(1).strip().strip("<>"))
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            assert (path.parent / target_path).resolve().exists(), (
                f"{path}: missing local documentation link {target}"
            )
        assert "../.github/workflows/quality.yml" in source
        assert "../.github/workflows/release.yml" in source
        assert "build-matrix.yml" not in source
        assert "main.yml" not in source


def test_known_release_workflows_and_sources_exist():
    for path in (
        ROOT / ".github" / "workflows" / "quality.yml",
        ROOT / ".github" / "workflows" / "release.yml",
        ROOT / "toolchain.json",
        ROOT / "dist" / "scoop" / "vigil.json",
    ):
        assert path.is_file(), path
