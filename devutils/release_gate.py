#!/usr/bin/env python3
"""Fail-closed Chromium security-refresh and release-input gate.

The gate deliberately does not fetch the network. A release job or maintainer
provides a small, reviewable upstream metadata JSON containing the stable
release/security-refresh dates and source URLs. This keeps the check
reproducible and makes the input that justified a release part of its receipt.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Mapping


REPORT_SCHEMA_VERSION = 1
DEFAULT_POLICY_NAME = "release_policy.json"
VERSION_PATTERN = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"required JSON file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def _parse_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date string (YYYY-MM-DD)")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date string (YYYY-MM-DD)") from exc


def _parse_nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _version_tuple(value: Any, field: str) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a version string")
    match = VERSION_PATTERN.match(value.strip())
    if not match:
        raise ValueError(f"{field} is not a Chromium-style version: {value!r}")
    return tuple(int(part or 0) for part in match.groups())


def _load_repository_inputs(repo_root: Path) -> dict[str, str]:
    toolchain = _read_json(repo_root / "toolchain.json")
    chromium = toolchain.get("chromium")
    if not chromium:
        raise ValueError("toolchain.json is missing the chromium version")
    _version_tuple(chromium, "toolchain.json chromium")

    ungoogled_revision_path = repo_root / "ungoogled-chromium" / "revision.txt"
    vigil_revision_path = repo_root / "revision.txt"
    try:
        ungoogled_revision = ungoogled_revision_path.read_text(
            encoding="utf-8"
        ).strip()
        vigil_revision = vigil_revision_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ValueError(f"required revision file is missing: {exc.filename}") from exc
    if not ungoogled_revision or not vigil_revision:
        raise ValueError("revision files must not be empty")

    vigil_manifest_path = repo_root / "dist" / "scoop" / "vigil.json"
    vigil_manifest = _read_json(vigil_manifest_path)
    vigil_version = vigil_manifest.get("version")
    if not isinstance(vigil_version, str) or not vigil_version:
        raise ValueError(f"missing Vigil version in {vigil_manifest_path}")
    _version_tuple(vigil_version, "Vigil version")

    return {
        "chromium": str(chromium),
        "ungoogled_revision": ungoogled_revision,
        "vigil_revision": vigil_revision,
        "vigil_version": vigil_version,
    }


def _load_policy(policy_path: Path) -> dict[str, Any]:
    policy = _read_json(policy_path)
    if policy.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported policy schema in {policy_path}: "
            f"{policy.get('schema_version')!r}"
        )
    max_age = _parse_nonnegative_int(
        policy.get("max_security_age_days"), "max_security_age_days"
    )
    max_lag = _parse_nonnegative_int(policy.get("max_major_lag"), "max_major_lag")
    if max_age == 0:
        raise ValueError("max_security_age_days must be greater than zero")
    policy["max_security_age_days"] = max_age
    policy["max_major_lag"] = max_lag
    return policy


def _load_upstream_metadata(metadata: Mapping[str, Any] | Path) -> dict[str, Any]:
    value = _read_json(metadata) if isinstance(metadata, Path) else dict(metadata)
    if value.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError(
            "upstream metadata schema_version must be "
            f"{REPORT_SCHEMA_VERSION}"
        )
    upstream = value.get("upstream")
    if not isinstance(upstream, dict):
        raise ValueError("upstream metadata must contain an upstream object")
    stable_version = upstream.get("stable_version")
    _version_tuple(stable_version, "upstream.stable_version")
    dates = []
    for field in ("stable_release_date", "security_refresh_date"):
        if upstream.get(field) is not None:
            dates.append(_parse_date(upstream[field], f"upstream.{field}"))
    if not dates:
        raise ValueError(
            "upstream metadata must contain stable_release_date or "
            "security_refresh_date"
        )
    source_url = upstream.get("source_url")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        raise ValueError("upstream.source_url must be an HTTPS URL")
    security_source_url = upstream.get("security_source_url", source_url)
    if not isinstance(security_source_url, str) or not security_source_url.startswith(
        "https://"
    ):
        raise ValueError("upstream.security_source_url must be an HTTPS URL")
    return value


def evaluate(
    repo_root: Path,
    metadata: Mapping[str, Any] | Path,
    *,
    as_of: date | None = None,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate release freshness and return a JSON-serializable report."""

    repo_root = repo_root.resolve()
    policy_path = policy_path or repo_root / DEFAULT_POLICY_NAME
    policy = _load_policy(policy_path)
    upstream_metadata = _load_upstream_metadata(metadata)
    revisions = _load_repository_inputs(repo_root)
    upstream = upstream_metadata["upstream"]
    as_of = as_of or date.today()

    current_version = _version_tuple(revisions["chromium"], "Chromium version")
    stable_version = _version_tuple(
        upstream["stable_version"], "upstream.stable_version"
    )
    major_lag = stable_version[0] - current_version[0]
    dates = [
        _parse_date(upstream[field], f"upstream.{field}")
        for field in ("stable_release_date", "security_refresh_date")
        if upstream.get(field) is not None
    ]
    refresh_date = max(dates)
    security_age_days = (as_of - refresh_date).days

    checks = [
        {
            "id": "upstream_metadata",
            "passed": True,
            "detail": "upstream version, date, and HTTPS sources are present",
        },
        {
            "id": "security_age",
            "passed": 0 <= security_age_days <= policy["max_security_age_days"],
            "detail": (
                f"{security_age_days} days since {refresh_date.isoformat()} "
                f"(maximum {policy['max_security_age_days']})"
            ),
        },
        {
            "id": "major_lag",
            "passed": 0 <= major_lag <= policy["max_major_lag"],
            "detail": (
                f"Chromium {revisions['chromium']} trails stable "
                f"{upstream['stable_version']} by {major_lag} major release(s) "
                f"(maximum {policy['max_major_lag']})"
            ),
        },
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": "pass" if passed else "fail",
        "as_of": as_of.isoformat(),
        "policy": {
            "path": str(policy_path),
            "max_security_age_days": policy["max_security_age_days"],
            "max_major_lag": policy["max_major_lag"],
        },
        "revisions": revisions,
        "upstream": {
            "stable_version": upstream["stable_version"],
            "stable_release_date": upstream.get("stable_release_date"),
            "security_refresh_date": upstream.get("security_refresh_date"),
            "reference_refresh_date": refresh_date.isoformat(),
            "security_age_days": security_age_days,
            "major_lag": major_lag,
            "source_url": upstream["source_url"],
            "security_source_url": upstream.get(
                "security_source_url", upstream["source_url"]
            ),
        },
        "checks": checks,
        "emergency_patch_path": policy.get("emergency_patch_path", []),
    }


def format_text(report: Mapping[str, Any]) -> str:
    """Render a short human-readable report without losing JSON output support."""

    lines = [
        f"Release gate: {str(report['status']).upper()}",
        f"Vigil {report['revisions']['vigil_version']} "
        f"(revision {report['revisions']['vigil_revision']})",
        f"Chromium {report['revisions']['chromium']} | "
        f"ungoogled revision {report['revisions']['ungoogled_revision']}",
        f"Upstream stable {report['upstream']['stable_version']} | "
        f"security age {report['upstream']['security_age_days']} day(s) | "
        f"major lag {report['upstream']['major_lag']}",
    ]
    for check in report["checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        lines.append(f"{marker} {check['id']}: {check['detail']}")
    if report["status"] != "pass":
        lines.append("Emergency path: refresh the upstream fix and metadata; do not bypass the gate.")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata",
        required=True,
        type=Path,
        help="JSON file containing the upstream stable/security refresh metadata.",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        help=f"Policy JSON (default: {DEFAULT_POLICY_NAME} at repo root).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Vigil repository root.",
    )
    parser.add_argument(
        "--as-of",
        help="Evaluate as of YYYY-MM-DD instead of today (useful for reproducible CI).",
    )
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )
    parser.add_argument("--output", type=Path, help="Optional report output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        as_of = _parse_date(args.as_of, "--as-of") if args.as_of else None
        policy_path = args.policy or args.repo_root / DEFAULT_POLICY_NAME
        report = evaluate(
            args.repo_root,
            args.metadata,
            as_of=as_of,
            policy_path=policy_path,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    rendered = (
        json.dumps(report, indent=2, sort_keys=True)
        if args.output_format == "json"
        else format_text(report)
    )
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
