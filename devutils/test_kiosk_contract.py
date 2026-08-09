import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KIOSK = ROOT / "kiosk"


def read(name):
    return (KIOSK / name).read_text(encoding="utf-8")


def test_cmd_launcher_accepts_only_one_url_and_delegates_parsing():
    source = read("vigil-kiosk.cmd")

    assert 'if not "%~2"==""' in source
    assert "-File \"%LAUNCHER%\"" in source
    assert "-KioskUrl \"%~1\"" in source
    assert "--autoplay-policy" not in source


def test_powershell_launcher_allowlists_url_and_arguments():
    source = read("vigil-kiosk.ps1")

    assert "TryCreate" in source
    assert "about:blank" in source
    assert "$uri.Scheme -ne 'https'" in source
    assert "Start-Process -FilePath $chromePath" in source
    assert "-ArgumentList $arguments" in source
    assert "Invoke-Expression" not in source
    assert "--autoplay-policy" not in source


def test_watchdog_uses_bounded_recovery_and_non_interpolated_launcher():
    watchdog = read("kiosk-watchdog.ps1")
    source = watchdog + read("install-watchdog.ps1")

    for marker in (
        "max_restart_attempts",
        "restart_window_seconds",
        "base_backoff_seconds",
        "restartTimes",
        "circuit breaker",
        "-ConfigPath",
        "created_event_source",
        "Remove-Item -LiteralPath $eventSourceKey -Recurse -Force",
    ):
        assert marker in source
    assert "@LAUNCHER@" not in source
    assert ".Replace('@LAUNCHER@'" not in source
    assert "Write-Host \"Set VigilKioskUrl policy: $KioskUrl\"" not in source
    assert "$MaxEventMessageLength = 512" in watchdog
    assert "$Message.Substring(0, $MaxEventMessageLength)" in watchdog


def test_kiosk_policy_owns_autoplay_decision():
    policy = json.loads((ROOT / "policies" / "vigil-kiosk.json").read_text(encoding="utf-8"))

    assert policy["AutoplayAllowed"] is False
    assert "--autoplay-policy" not in read("vigil-kiosk.ps1")
