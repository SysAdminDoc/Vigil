import json
from pathlib import Path

from privacy_probe import run_probe


ROOT = Path(__file__).resolve().parents[1]


def test_first_run_privacy_probe_passes_without_network_access():
    report = run_probe(ROOT)

    assert report["status"] == "pass", report
    assert report["network_before_explicit_opt_in"] is False
    assert report["search_suggestions"] == {
        "enabled": True,
        "endpoint": "https://duckduckgo.com/ac/",
        "request_requires_typed_query": True,
    }


def test_initial_preferences_have_no_telemetry_or_unapproved_urls():
    prefs = json.loads((ROOT / "initial_preferences").read_text(encoding="utf-8"))
    assert prefs["search"]["suggest_enabled"] is True
    assert prefs["safebrowsing"]["enabled"] is True
    assert prefs["safebrowsing"]["scout_reporting_enabled"] is False
    assert prefs["safebrowsing"]["extended_reporting_enabled"] is False
    assert "favicon_url" not in prefs["default_search_provider_data"]["template_url_data"]
