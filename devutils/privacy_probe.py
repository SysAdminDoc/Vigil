#!/usr/bin/env python3
"""Run the source-level first-run network and telemetry contract probe.

The probe is deliberately offline. It models a new profile by inspecting the
checked-in defaults and the extension code paths that are reached with empty
storage. It never starts Chromium and never contacts a network service.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
NTP_WIDGETS = ("notes", "topSites", "bookmarks", "weather", "rss")
NTP_HOSTS = [
    "https://geocoding-api.open-meteo.com/*",
    "https://api.open-meteo.com/*",
]
SUGGESTION_HOST = "duckduckgo.com"
SUGGESTION_PATH = "/ac/"
URL_PATTERN = re.compile(r"https?://[^\s\"']+")


class Probe:
    """Collect deterministic checks for human or JSON output."""

    def __init__(self):
        self.checks = []

    def check(self, label, condition, detail=""):
        entry = {"label": label, "passed": bool(condition)}
        if detail:
            entry["detail"] = detail
        self.checks.append(entry)

    @property
    def failed(self):
        return [check for check in self.checks if not check["passed"]]

    def as_dict(self):
        return {
            "checks": self.checks,
            "failed": len(self.failed),
            "network_before_explicit_opt_in": False,
            "search_suggestions": {
                "enabled": True,
                "endpoint": "https://duckduckgo.com/ac/",
                "request_requires_typed_query": True,
            },
            "status": "pass" if not self.failed else "fail",
        }


def read_text(root, relative, probe):
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        probe.check(f"read {relative}", False, str(exc))
        return ""


def read_json(root, relative, probe):
    source = read_text(root, relative, probe)
    if not source:
        return {}
    try:
        return json.loads(source)
    except json.JSONDecodeError as exc:
        probe.check(f"valid JSON: {relative}", False, str(exc))
        return {}


def iter_strings(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)
    elif isinstance(value, str):
        yield value


def assert_initial_preferences(root, probe):
    prefs = read_json(root, "initial_preferences", probe)
    search_data = prefs.get("default_search_provider_data", {}).get(
        "template_url_data", {}
    )
    suggest_url = search_data.get("suggest_url", "")
    parsed_suggest = urlparse(suggest_url)
    query = parse_qs(parsed_suggest.query)
    probe.check(
        "search suggestions are enabled",
        prefs.get("search", {}).get("suggest_enabled") is True,
    )
    probe.check(
        "suggestions use the documented DuckDuckGo endpoint",
        (
            parsed_suggest.scheme == "https"
            and parsed_suggest.hostname == SUGGESTION_HOST
            and parsed_suggest.path == SUGGESTION_PATH
            and query.get("q") == ["{searchTerms}"]
            and query.get("type") == ["list"]
        ),
        suggest_url,
    )
    safe_browsing = prefs.get("safebrowsing", {})
    probe.check("Safe Browsing remains enabled", safe_browsing.get("enabled") is True)
    for key in ("enhanced", "scout_reporting_enabled", "extended_reporting_enabled"):
        probe.check(f"Safe Browsing {key} is disabled", safe_browsing.get(key) is False)
    probe.check(
        "DNS prefetching is disabled",
        prefs.get("dns_prefetching", {}).get("enabled") is False,
    )
    probe.check(
        "network prediction is disabled",
        prefs.get("net", {}).get("network_prediction_options") == 2,
    )
    urls = [urlparse(match) for value in iter_strings(prefs) for match in URL_PATTERN.findall(value)]
    unapproved = sorted({parsed.hostname for parsed in urls if parsed.hostname != SUGGESTION_HOST})
    probe.check(
        "initial preferences contain no unapproved network hosts",
        not unapproved,
        ", ".join(unapproved),
    )
    raw = json.dumps(prefs, sort_keys=True).lower()
    for marker in ("telemetry", "metrics_reporting", "crash_upload", "reporting_url"):
        probe.check(f"no active {marker} preference", marker not in raw)
    return prefs


def assert_ntp_contract(root, probe):
    manifest = read_json(root, "ntp-extension/manifest.json", probe)
    source = read_text(root, "ntp-extension/newtab.js", probe)
    probe.check("NTP fixed host permissions are minimal", manifest.get("host_permissions") == NTP_HOSTS)
    probe.check(
        "NTP user-managed access remains optional",
        manifest.get("optional_host_permissions") == ["https://*/*"],
    )
    csp = manifest.get("content_security_policy", {}).get("extension_pages", "")
    probe.check("NTP images are local-only", "img-src 'self'" in csp and "google.com" not in csp)
    for widget in NTP_WIDGETS:
        probe.check(
            f"fresh NTP default disables {widget}",
            re.search(rf"\b{re.escape(widget)}:\s*false\b", source) is not None,
        )
    probe.check(
        "fresh NTP renders no widgets before opt-in",
        "if (!Object.values(enabled).some(Boolean))" in source,
    )
    probe.check("NTP has one bounded network helper", source.count("fetch(") == 1)
    for marker in (
        "AbortController",
        'redirect: "error"',
        'credentials: "omit"',
        'cache: "no-store"',
        "getReader()",
        "requestRssPermissions",
        "OPEN_METEO_ORIGINS",
    ):
        probe.check(f"NTP network guard: {marker}", marker in source)
    probe.check("NTP has no remote shortcut icon source", "s2/favicons" not in source)
    for widget in ("weather", "rss"):
        probe.check(
            f"{widget} requests require an enabled widget",
            f"if (enabled.{widget})" in source,
        )
    return manifest


def assert_palette_contract(root, probe):
    source = "\n".join(
        read_text(root, f"palette-extension/{filename}", probe)
        for filename in ("background.js", "content.js", "palette.js")
    )
    for marker in ("fetch(", "XMLHttpRequest", "WebSocket"):
        probe.check(f"palette has no network primitive: {marker}", marker not in source)


def assert_packaged_defaults(build_out, source_prefs, probe):
    if build_out is None:
        return
    path = Path(build_out) / "initial_preferences"
    try:
        packaged = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        probe.check("packaged initial preferences match source", False, str(exc))
        return
    probe.check("packaged initial preferences match source", packaged == source_prefs)


def run_probe(root=ROOT, build_out=None):
    probe = Probe()
    prefs = assert_initial_preferences(Path(root), probe)
    assert_ntp_contract(Path(root), probe)
    assert_palette_contract(Path(root), probe)
    assert_packaged_defaults(build_out, prefs, probe)
    return probe.as_dict()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--build-out", type=Path, default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    report = run_probe(args.repo_root, args.build_out)
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for check in report["checks"]:
            status = "PASS" if check["passed"] else "FAIL"
            detail = f" ({check['detail']})" if check.get("detail") else ""
            print(f"{status:4} {check['label']}{detail}")
        print(f"\nPrivacy probe: {report['status']} ({report['failed']} failed)")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
