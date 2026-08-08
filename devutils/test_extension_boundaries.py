import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_manifest(extension):
    path = ROOT / extension / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_ntp_network_permissions_are_fixed_or_user_managed():
    manifest = read_manifest("ntp-extension")

    assert manifest["host_permissions"] == [
        "https://geocoding-api.open-meteo.com/*",
        "https://api.open-meteo.com/*",
    ]
    assert manifest["optional_host_permissions"] == ["https://*/*"]
    assert "https://www.google.com/s2/favicons" not in manifest[
        "content_security_policy"
    ]["extension_pages"]


def test_palette_has_no_automatic_all_site_injection():
    manifest = read_manifest("palette-extension")

    assert "host_permissions" not in manifest
    assert "content_scripts" not in manifest
    assert {"activeTab", "scripting"}.issubset(manifest["permissions"])


def test_extension_permissions_do_not_expand_into_sensitive_surfaces():
    manifests = [read_manifest("ntp-extension"), read_manifest("palette-extension")]
    permissions = {
        permission
        for manifest in manifests
        for permission in manifest.get("permissions", [])
    }

    assert not permissions.intersection(
        {"cookies", "identity", "nativeMessaging", "webRequest", "downloads"}
    )


def test_extension_sources_reject_wildcard_messaging_and_dangerous_code():
    paths = [
        ROOT / "ntp-extension" / "newtab.js",
        ROOT / "palette-extension" / "background.js",
        ROOT / "palette-extension" / "content.js",
        ROOT / "palette-extension" / "palette.js",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert not re.search(r"postMessage\s*\([^;]*,\s*['\"]\*['\"]", source, re.DOTALL)
    assert not re.search(r"\beval\s*\(|new\s+Function\s*\(", source)
    assert not (ROOT / "palette-extension" / "background.js").read_text(
        encoding="utf-8"
    ).lower().__contains__("file:")
    assert "innerHTML" not in (ROOT / "ntp-extension" / "newtab.js").read_text(
        encoding="utf-8"
    )
    assert "www.google.com/s2/favicons" not in source


def test_ntp_widget_requests_are_bounded_and_allowlisted():
    source = (ROOT / "ntp-extension" / "newtab.js").read_text(encoding="utf-8")

    for marker in (
        "SETTINGS_SCHEMA_VERSION",
        "AbortController",
        'redirect: "error"',
        'credentials: "omit"',
        'cache: "no-store"',
        'getReader()',
        '"content-length"',
        "requestRssPermissions",
        "OPEN_METEO_ORIGINS",
    ):
        assert marker in source


def test_palette_bridge_checks_exact_source_and_origin():
    content = (ROOT / "palette-extension" / "content.js").read_text(encoding="utf-8")
    palette = (ROOT / "palette-extension" / "palette.js").read_text(encoding="utf-8")

    for source in (content, palette):
        assert "event.source" in source
        assert "event.origin" in source
    assert "extensionOrigin" in content
    assert "parentOrigin" in palette
