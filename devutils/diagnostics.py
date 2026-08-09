#!/usr/bin/env python3
"""Create structured, privacy-safe diagnostics for Vigil release support."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DIAGNOSTICS_SCHEMA_VERSION = 1
REDACTED_VALUE = "[REDACTED]"
_CHECK_ID_RE = re.compile(r"[^a-z0-9_.-]+", re.IGNORECASE)
_URL_RE = re.compile(r"(?i)\b(?:https?|ftp)://[^\s<>\"']+")
_WINDOWS_PATH_RE = re.compile(r"(?i)(?<![\w])(?:[a-z]:[\\/]|\\\\)[^\s<>\"']+")
_POSIX_PATH_RE = re.compile(
    r"(?i)(?<![\w])/(?:users|home|tmp|var/tmp|var/folders)/[^\s<>\"']+"
)
_PROFILE_PATH_RE = re.compile(
    r"(?i)(?<![\w])(?:[a-z]:[\\/])?"
    r"(?:users|profiles|appdata|localappdata|programdata|temp|tmp|userdata)"
    r"[\\/][^\s<>\"']+"
)
_SECRET_KEY_RE = re.compile(
    r"(?i)(?:password|passwd|secret|token|authorization|cookie|credential|"
    r"private[_-]?key|api[_-]?key|access[_-]?key|refresh[_-]?token)"
)


def redact(value: Any, *, key: str | None = None) -> Any:
    """Return a JSON-safe value with paths, URLs, and keyed secrets removed."""

    if key is not None and _SECRET_KEY_RE.search(key):
        return REDACTED_VALUE
    if isinstance(value, Mapping):
        return {str(item_key): redact(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact(item) for item in value]
    if not isinstance(value, str):
        return value
    sanitized = _URL_RE.sub(REDACTED_VALUE, value)
    sanitized = _WINDOWS_PATH_RE.sub(REDACTED_VALUE, sanitized)
    sanitized = _POSIX_PATH_RE.sub(REDACTED_VALUE, sanitized)
    return _PROFILE_PATH_RE.sub(REDACTED_VALUE, sanitized)


def stable_check_id(check_id: str) -> str:
    """Normalize a check identifier so it is stable and machine-readable."""

    normalized = _CHECK_ID_RE.sub("_", str(check_id).strip().lower()).strip("_.-")
    if not normalized:
        raise ValueError("diagnostic check IDs must contain an alphanumeric character")
    return normalized


def make_check(
    check_id: str,
    passed: bool,
    *,
    severity: str = "error",
    detail: str = "",
    evidence: Any = None,
    failure_code: str | None = None,
    skipped: bool = False,
) -> dict[str, Any]:
    """Build one stable diagnostic check and redact its human evidence."""

    if severity not in {"error", "warning", "info"}:
        raise ValueError(f"unsupported diagnostic severity: {severity}")
    normalized_id = stable_check_id(check_id)
    failed = not passed and not skipped
    if failed and not failure_code:
        failure_code = f"VIGIL_{normalized_id.upper().replace('.', '_').replace('-', '_')}_FAILED"
    if not failed:
        failure_code = None
    return {
        "id": normalized_id,
        "passed": bool(passed),
        "severity": severity,
        "failure_code": failure_code,
        "skipped": bool(skipped),
        "detail": redact(detail),
        "evidence": redact({} if evidence is None else evidence),
    }


def diagnostics_status(checks: Sequence[Mapping[str, Any]]) -> str:
    """Return fail only when an unsuppressed error-level check failed."""

    for check in checks:
        if (
            check.get("severity", "error") == "error"
            and not check.get("passed", False)
            and not check.get("skipped", False)
        ):
            return "fail"
    return "pass"


def make_diagnostics_report(
    *,
    kind: str,
    checks: Sequence[Mapping[str, Any]],
    source: Mapping[str, Any] | None = None,
    architecture: Mapping[str, Any] | None = None,
    counts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable report envelope shared by release and smoke tooling."""

    normalized_checks = [redact(dict(check)) for check in checks]
    failures = sorted(
        {
            str(check["failure_code"])
            for check in normalized_checks
            if check.get("failure_code") and not check.get("passed", False)
        }
    )
    warnings = sorted(
        {
            str(check["failure_code"])
            for check in normalized_checks
            if check.get("failure_code")
            and not check.get("passed", False)
            and check.get("severity") == "warning"
        }
    )
    return {
        "schema_version": DIAGNOSTICS_SCHEMA_VERSION,
        "kind": kind,
        "status": diagnostics_status(normalized_checks),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": redact({} if source is None else source),
        "architecture": redact({} if architecture is None else architecture),
        "checks": normalized_checks,
        "failure_codes": failures,
        "warning_codes": warnings,
        "counts": redact({} if counts is None else counts),
        "redaction": {
            "urls": "redacted",
            "absolute_paths": "redacted",
            "profile_paths": "redacted",
            "keyed_secrets": "redacted",
        },
    }


def build_release_diagnostics(
    *,
    records: Sequence[Mapping[str, Any]],
    artifact_contract: Mapping[str, Any],
    manifest_checks: Sequence[Mapping[str, Any]],
    strict_manifests: bool,
    insecure_downloads: bool,
) -> dict[str, Any]:
    """Normalize release-receipt checks with stable IDs and failure codes."""

    checks = [
        make_check(
            "artifacts.present",
            bool(records),
            detail=f"{len(records)} release artifact(s) recorded",
            evidence={"count": len(records)},
            failure_code="NO_RELEASE_ARTIFACTS",
        ),
        make_check(
            "artifacts.architecture_contract",
            bool(artifact_contract.get("passed")),
            detail="required installer and archive architectures are present",
            evidence=artifact_contract,
            failure_code="MISSING_ARCHITECTURE_ARTIFACT",
        ),
        make_check(
            "package_manifests",
            all(check.get("passed", False) for check in manifest_checks),
            severity="error" if strict_manifests else "warning",
            detail=(
                "package-manager manifests contain no placeholders"
                if strict_manifests
                else "manifest placeholders are advisory until strict validation"
            ),
            evidence={"strict": strict_manifests, "manifests": manifest_checks},
            failure_code="PACKAGE_MANIFEST_PLACEHOLDER",
        ),
        make_check(
            "release_safety.insecure_downloads",
            not insecure_downloads,
            detail="SSL verification bypass is disabled",
            evidence={"enabled": insecure_downloads},
            failure_code="INSECURE_DOWNLOADS_ENABLED",
        ),
    ]
    artifact_contract = dict(artifact_contract)
    return make_diagnostics_report(
        kind="release-diagnostics",
        checks=checks,
        architecture={
            "required": artifact_contract.get("required_architectures", []),
            "installers": artifact_contract.get("installer_architectures", []),
            "archives": artifact_contract.get("archive_architectures", []),
            "missing": artifact_contract.get("missing_architectures", []),
        },
        counts={
            "artifacts": len(records),
            "manifest_files": len(manifest_checks),
        },
    )


def _normalize_check(
    value: Mapping[str, Any], *, prefix: str, default_severity: str = "error"
) -> dict[str, Any]:
    check_id = str(value.get("id", "unknown"))
    if prefix and not check_id.startswith(f"{prefix}."):
        check_id = f"{prefix}.{check_id}"
    status = value.get("status")
    skipped = bool(value.get("skipped", status == "skip"))
    passed = bool(value.get("passed", status in {"pass", "skip"}))
    return make_check(
        check_id,
        passed,
        severity=str(value.get("severity", default_severity)),
        detail=str(value.get("detail", "")),
        evidence=value.get("evidence", {}),
        failure_code=value.get("failure_code"),
        skipped=skipped,
    )


def build_support_receipt(
    release_report: Mapping[str, Any],
    smoke_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a support receipt that contains no identifying URLs or paths."""

    source = release_report.get("source", {})
    if not isinstance(source, Mapping):
        source = {}
    toolchain = source.get("toolchain", {})
    if not isinstance(toolchain, Mapping):
        toolchain = {}
    source_summary = {
        "vigil_version": source.get("vigil_version"),
        "vigil_revision": source.get("vigil_revision"),
        "chromium": source.get("chromium"),
        "ungoogled_revision": source.get("ungoogled_revision"),
        "git_revision": source.get("git_revision"),
        "toolchain_ids": dict(toolchain),
    }
    contract = release_report.get("artifact_contract", {})
    if not isinstance(contract, Mapping):
        contract = {}
    architecture = {
        "required": contract.get("required_architectures", []),
        "installers": contract.get("installer_architectures", []),
        "archives": contract.get("archive_architectures", []),
        "missing": contract.get("missing_architectures", []),
        "artifacts": [
            {
                key: artifact.get(key)
                for key in ("name", "kind", "architecture", "size", "sha256")
                if key in artifact
            }
            for artifact in release_report.get("artifacts", [])
            if isinstance(artifact, Mapping)
        ],
    }

    checks: list[dict[str, Any]] = [
        make_check(
            "release.receipt",
            release_report.get("status") == "pass",
            detail=f"release receipt status: {release_report.get('status', 'unknown')}",
            evidence={"schema_version": release_report.get("schema_version")},
            failure_code="RELEASE_RECEIPT_FAILED",
        )
    ]
    release_diagnostics = release_report.get("diagnostics")
    if isinstance(release_diagnostics, Mapping):
        for value in release_diagnostics.get("checks", []):
            if isinstance(value, Mapping):
                checks.append(_normalize_check(value, prefix="release"))
    else:
        checks.append(
            make_check(
                "release.diagnostics",
                False,
                detail="release receipt does not contain structured diagnostics",
                failure_code="RELEASE_DIAGNOSTICS_MISSING",
            )
        )
    if isinstance(smoke_report, Mapping):
        checks.append(
            make_check(
                "smoke.summary",
                smoke_report.get("status") == "pass",
                detail=f"smoke test status: {smoke_report.get('status', 'unknown')}",
                evidence={"counts": smoke_report.get("counts", {})},
                failure_code="SMOKE_TEST_FAILED",
            )
        )
        for value in smoke_report.get("checks", []):
            if isinstance(value, Mapping):
                checks.append(_normalize_check(value, prefix="smoke"))

    return make_diagnostics_report(
        kind="support-receipt",
        checks=checks,
        source=source_summary,
        architecture=architecture,
        counts={
            "release_artifacts": len(architecture["artifacts"]),
            "checks": len(checks),
            "smoke_checks": len(smoke_report.get("checks", []))
            if isinstance(smoke_report, Mapping)
            else 0,
        },
    )


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object and reject malformed or non-object documents."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read JSON object from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    """Write a diagnostic report without exposing a partially-written receipt."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--receipt",
        type=Path,
        default=Path("build/release-receipt.json"),
        help="Release receipt to summarize (default: build/release-receipt.json).",
    )
    parser.add_argument("--smoke-report", type=Path, help="Optional smoke-test report JSON.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/support-receipt.json"),
        help="Privacy-safe support receipt output path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        release_report = load_json_object(args.receipt)
        smoke_report = load_json_object(args.smoke_report) if args.smoke_report else None
        report = build_support_receipt(release_report, smoke_report)
        write_json_atomic(args.output, report)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
