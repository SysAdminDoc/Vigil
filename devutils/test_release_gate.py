import json
from datetime import date

from devutils.release_gate import evaluate, format_text


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def seed_repo(tmp_path):
    write_json(
        tmp_path / "toolchain.json",
        {"chromium": "149.0.1.2"},
    )
    (tmp_path / "revision.txt").write_text("7\n", encoding="utf-8")
    (tmp_path / "ungoogled-chromium" / "revision.txt").parent.mkdir()
    (tmp_path / "ungoogled-chromium" / "revision.txt").write_text(
        "3\n", encoding="utf-8"
    )
    write_json(tmp_path / "dist" / "scoop" / "vigil.json", {"version": "0.2.1"})
    write_json(
        tmp_path / "release_policy.json",
        {
            "schema_version": 1,
            "max_security_age_days": 14,
            "max_major_lag": 1,
            "emergency_patch_path": ["refresh"],
        },
    )


def metadata(stable_version="149.0.2.0", release_date="2026-08-01"):
    return {
        "schema_version": 1,
        "upstream": {
            "stable_version": stable_version,
            "stable_release_date": release_date,
            "security_refresh_date": release_date,
            "source_url": "https://example.test/chrome-release",
            "security_source_url": "https://example.test/chromium-security",
        },
    }


def test_evaluate_reports_all_revisions_and_passes(tmp_path):
    seed_repo(tmp_path)

    report = evaluate(
        tmp_path,
        metadata(),
        as_of=date(2026, 8, 8),
    )

    assert report["status"] == "pass"
    assert report["revisions"] == {
        "chromium": "149.0.1.2",
        "ungoogled_revision": "3",
        "vigil_revision": "7",
        "vigil_version": "0.2.1",
    }
    assert report["upstream"]["security_age_days"] == 7
    assert {check["id"] for check in report["checks"]} == {
        "upstream_metadata",
        "security_age",
        "major_lag",
    }
    assert "Release gate: PASS" in format_text(report)


def test_evaluate_fails_for_stale_and_major_lagging_source(tmp_path):
    seed_repo(tmp_path)

    report = evaluate(
        tmp_path,
        metadata(stable_version="151.0.0.0", release_date="2026-07-01"),
        as_of=date(2026, 8, 8),
    )

    assert report["status"] == "fail"
    failed = {check["id"] for check in report["checks"] if not check["passed"]}
    assert failed == {"security_age", "major_lag"}


def test_evaluate_rejects_missing_https_source(tmp_path):
    seed_repo(tmp_path)
    bad = metadata()
    bad["upstream"]["source_url"] = "http://example.test/not-a-source"

    try:
        evaluate(tmp_path, bad, as_of=date(2026, 8, 8))
    except ValueError as exc:
        assert "HTTPS URL" in str(exc)
    else:
        raise AssertionError("insecure upstream source was accepted")
