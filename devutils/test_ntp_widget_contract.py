import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def ntp_source():
    return (ROOT / "ntp-extension" / "newtab.js").read_text(encoding="utf-8")


def test_every_widget_is_opt_in_and_has_a_local_empty_or_error_state():
    source = ntp_source()

    for widget in ("notes", "topSites", "bookmarks", "weather", "rss"):
        assert re.search(rf"\b{re.escape(widget)}:\s*false\b", source)
        assert f"if (enabled.{widget})" in source
    for key in (
        "noTopSites",
        "chooseBookmarkFolder",
        "chooseCity",
        "weatherUnavailable",
        "feedsUnavailable",
    ):
        assert f't("{key}")' in source
    assert "widgetsEl.style.display = \"none\"" in source


def test_widget_requests_use_allowlists_limits_and_no_store_cache():
    source = ntp_source()
    manifest = json.loads(
        (ROOT / "ntp-extension" / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["host_permissions"] == [
        "https://geocoding-api.open-meteo.com/*",
        "https://api.open-meteo.com/*",
    ]
    assert manifest["optional_host_permissions"] == ["https://*/*"]
    for marker in (
        "const FETCH_TIMEOUT_MS = 8000",
        "const MAX_JSON_BYTES = 256 * 1024",
        "const MAX_RSS_BYTES = 512 * 1024",
        'redirect: "error"',
        'credentials: "omit"',
        'cache: "no-store"',
        'if (!allowedOrigins.has(parsed.origin))',
        'if (!contentTypes.includes(contentType))',
        'if (total > maxBytes)',
        "await reader.cancel()",
    ):
        assert marker in source
    assert source.count("maxBytes: MAX_JSON_BYTES") == 2
    assert source.count("maxBytes: MAX_RSS_BYTES") == 1
    assert source.index("hasRssPermissions(feeds).then") < source.index(
        "Promise.all(feeds.map"
    )


def test_widget_storage_is_versioned_and_bounded_before_persistence():
    source = ntp_source()

    for marker in (
        "const SETTINGS_SCHEMA_VERSION = 1",
        "schemaVersion: SETTINGS_SCHEMA_VERSION",
        "const MAX_SHORTCUTS = 12",
        "const MAX_SHORTCUT_NAME = 80",
        "const MAX_URL_LENGTH = 2048",
        "const MAX_NOTES_LENGTH = 10000",
        "const MAX_CITY_LENGTH = 100",
        "const MAX_RSS_FEEDS = 3",
        "const MAX_RSS_FEED_LENGTH = 2048",
        "const normalized = normalizeSettings(s)",
    ):
        assert marker in source
