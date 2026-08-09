import json

from devutils.diagnostics import (
    build_release_diagnostics,
    build_support_receipt,
    make_check,
)
from devutils.smoke_test import Result


def test_checks_have_stable_shape_and_redact_sensitive_evidence():
    check = make_check(
        "profile-path-check",
        False,
        detail=r"Could not read C:\Users\patient\AppData\Local\Vigil\UserData",
        evidence={
            "url": "https://clinic.example.test/private?token=abc",
            "token": "secret-token",
        },
        failure_code="PROFILE_READ_FAILED",
    )

    assert set(check) == {
        "id",
        "passed",
        "severity",
        "failure_code",
        "skipped",
        "detail",
        "evidence",
    }
    serialized = json.dumps(check)
    assert "clinic.example.test" not in serialized
    assert "C:\\Users" not in serialized
    assert "secret-token" not in serialized
    assert check["failure_code"] == "PROFILE_READ_FAILED"


def test_release_diagnostics_reports_architecture_and_manifest_failures():
    report = build_release_diagnostics(
        records=[{"name": "vigil_x64.zip"}],
        artifact_contract={
            "required_architectures": ["x64", "arm64"],
            "installer_architectures": ["x64"],
            "archive_architectures": ["x64"],
            "missing_architectures": ["arm64"],
            "passed": False,
        },
        manifest_checks=[{"path": "dist/scoop/vigil.json", "passed": False}],
        strict_manifests=True,
        insecure_downloads=False,
    )

    assert report["status"] == "fail"
    assert {check["id"] for check in report["checks"]} == {
        "artifacts.present",
        "artifacts.architecture_contract",
        "package_manifests",
        "release_safety.insecure_downloads",
    }
    assert "MISSING_ARCHITECTURE_ARTIFACT" in report["failure_codes"]
    assert "PACKAGE_MANIFEST_PLACEHOLDER" in report["failure_codes"]


def test_support_receipt_combines_release_and_smoke_without_private_data():
    release_diagnostics = build_release_diagnostics(
        records=[
            {
                "name": "vigil_x64.zip",
                "kind": "archive",
                "architecture": "x64",
                "size": 12,
                "sha256": "A" * 64,
                "path": r"C:\Users\builder\build\vigil_x64.zip",
                "release_url": "https://github.example.test/releases/v0.2.1/vigil_x64.zip",
            }
        ],
        artifact_contract={
            "required_architectures": ["x64"],
            "installer_architectures": ["x64"],
            "archive_architectures": ["x64"],
            "missing_architectures": [],
            "passed": True,
        },
        manifest_checks=[{"path": "dist/scoop/vigil.json", "passed": True}],
        strict_manifests=True,
        insecure_downloads=False,
    )
    release = {
        "schema_version": 1,
        "status": "pass",
        "source": {
            "vigil_version": "0.2.1",
            "vigil_revision": "7",
            "chromium": "145.0.7632.159",
            "ungoogled_revision": "1",
            "git_revision": "a" * 40,
            "toolchain": {"clang": "22.1.0", "gn": "2315"},
            "source_url": "https://example.test/source",
        },
        "artifact_contract": {
            "required_architectures": ["x64"],
            "installer_architectures": ["x64"],
            "archive_architectures": ["x64"],
            "missing_architectures": [],
        },
        "artifacts": [
            {
                "name": "vigil_x64.zip",
                "kind": "archive",
                "architecture": "x64",
                "size": 12,
                "sha256": "A" * 64,
                "path": r"C:\Users\builder\build\vigil_x64.zip",
                "release_url": "https://github.example.test/releases/v0.2.1/vigil_x64.zip",
            }
        ],
        "diagnostics": release_diagnostics,
    }
    smoke = {
        "status": "pass",
        "counts": {"passed": 2, "failed": 0, "skipped": 0},
        "checks": [
            make_check(
                "smoke.output",
                True,
                detail=r"checked C:\Users\patient\AppData\Local\Vigil",
                evidence={"url": "https://patient.example.test"},
            )
        ],
    }

    support = build_support_receipt(release, smoke)
    serialized = json.dumps(support)

    assert support["status"] == "pass"
    assert support["source"]["vigil_version"] == "0.2.1"
    assert support["architecture"]["required"] == ["x64"]
    assert "release.artifacts.architecture_contract" in {
        check["id"] for check in support["checks"]
    }
    assert "github.example.test" not in serialized
    assert "patient.example.test" not in serialized
    assert "C:\\Users" not in serialized
    assert "release_url" not in serialized


def test_smoke_result_emits_structured_redacted_report():
    result = Result()
    result.fail(
        "profile lookup",
        r"failed at C:\Users\patient\AppData\Local\Vigil\UserData",
        failure_code="PROFILE_LOOKUP_FAILED",
    )

    report = result.diagnostics_report()

    assert report["status"] == "fail"
    assert report["failure_codes"] == ["PROFILE_LOOKUP_FAILED"]
    assert "C:\\Users" not in json.dumps(report)
