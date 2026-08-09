"""Static contract checks for Vigil's opt-in Global Privacy Control path."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = (
    ROOT
    / "patches"
    / "ungoogled-chromium"
    / "windows"
    / "windows-global-privacy-control.patch"
)


def test_patch_is_in_series_and_covers_browser_contract() -> None:
    series = (ROOT / "patches" / "series").read_text(encoding="utf-8")
    patch = PATCH.read_text(encoding="utf-8")

    assert PATCH.relative_to(ROOT / "patches").as_posix() in series
    for token in (
        '"Sec-GPC", "1"',
        "navigator.globalPrivacyControl",
        "globalPrivacyControl",
        "vigil.global_privacy_control_enabled",
        "SetGlobalPrivacyControlEnabled",
        "navigator_global_privacy_control.idl",
        "GlobalPrivacyControlDisabled",
        "GlobalPrivacyControlEnabled",
    ):
        assert token in patch


def test_initial_preference_is_explicitly_off() -> None:
    preferences = json.loads(
        (ROOT / "initial_preferences").read_text(encoding="utf-8")
    )

    assert preferences["vigil.global_privacy_control_enabled"] is False


def test_settings_overlay_exposes_opt_in_toggle_and_caveat() -> None:
    overlay = (
        ROOT
        / "chromium_src"
        / "chrome"
        / "browser"
        / "resources"
        / "settings"
        / "privacy_page"
        / "do_not_track_toggle.html"
    ).read_text(encoding="utf-8")

    assert 'pref="{{prefs.vigil_global_privacy_control_enabled}}"' in overlay
    assert (
        "Ask websites not to sell or share your information. Websites may "
        "ignore this signal."
    ) in overlay
