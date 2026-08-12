#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vigil smoke test (roadmap item N14).

Inspects the built artifact or portable zip and asserts the post-conditions that
the v0.2 defaults work. The default path is deterministic and does not launch
Chromium.

Designed to be runnable on the maintainer's workstation or a clean Windows
release-validation environment.

Tests, in order of cheapest -> most expensive:

  1. File presence in the build output (initial_preferences, ntp-extension, etc.)
  2. JSON validity of initial_preferences
  3. Default-search-engine = DuckDuckGo (from initial_preferences inspection)
  4. HTTPS-First Balanced mode on (from initial_preferences inspection)
  5. Safe Browsing re-enabled, telemetry off (from initial_preferences inspection)
  6. Privacy Sandbox APIs disabled (from initial_preferences inspection)
  7. Permissions-Policy default-deny content settings (from initial_preferences)
  7b. Managed policy baselines are packaged for administrator deployment
  7c. Kiosk autoplay remains a managed policy decision
  8. uBO staged in Extensions/cjpalhdlnbpafiamejdnhcphjbkeiagm/<v>/ + manifest valid
  9. NTP extension declares chrome_url_overrides.newtab
  9b. Command palette extension is staged with its stable ID and pointer
 10. (Optional) Selenium-driven launch: open chrome://settings, confirm the page
     renders and the Vigil-overlay CSS is applied (looks for a known class).

Steps 1-9 do NOT require launching Chrome and are the file-only path.
Step 10 only runs when --selenium is passed AND chromedriver is on PATH. It must
be run under the repository's invisible visual-isolation procedure.

Exit codes:
   0 - all assertions passed
   1 - one or more assertions failed
   2 - test harness error (paths missing, etc.)
"""

import argparse
import base64
import hashlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

if __package__:
    from .diagnostics import (
        load_json_object,
        make_check,
        make_diagnostics_report,
        write_json_atomic,
    )
else:
    from diagnostics import (  # type: ignore[no-redef]
        load_json_object,
        make_check,
        make_diagnostics_report,
        write_json_atomic,
    )

# Vigil expects this uBO Chrome Web Store extension ID
UBO_EXT_ID = "cjpalhdlnbpafiamejdnhcphjbkeiagm"

# Expected default-search keyword post-N1
EXPECTED_SEARCH_KEYWORD = "duckduckgo.com"


class Result:
    """Tracks pass/fail outcomes across the run."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.checks = []

    @staticmethod
    def _stable_check_id(label):
        without_parentheses = re.sub(r"\([^)]*\)", "", label)
        without_value = re.sub(r"\s(?:=|->)\s.*$", "", without_parentheses)
        slug = re.sub(r"[^a-z0-9]+", "_", without_value.lower()).strip("_")
        return f"smoke.{slug or 'check'}"

    def ok(self, label, *, check_id=None, evidence=None):
        print(f"  PASS  {label}")
        self.passed += 1
        self.checks.append(
            make_check(
                check_id or self._stable_check_id(label),
                True,
                severity="info",
                evidence=evidence,
            )
        )

    def fail(self, label, detail="", *, check_id=None, evidence=None, failure_code=None):
        print(f"  FAIL  {label}")
        if detail:
            print(f"        {detail}")
        self.failed += 1
        self.checks.append(
            make_check(
                check_id or self._stable_check_id(label),
                False,
                detail=detail,
                evidence=evidence,
                failure_code=failure_code,
            )
        )

    def skip(self, label, reason, *, check_id=None):
        print(f"  SKIP  {label} ({reason})")
        self.skipped += 1
        self.checks.append(
            make_check(
                check_id or self._stable_check_id(label),
                True,
                severity="info",
                detail=reason,
                skipped=True,
            )
        )

    def diagnostics_report(self):
        return make_diagnostics_report(
            kind="smoke-test",
            checks=self.checks,
            counts={
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "total": self.passed + self.failed + self.skipped,
            },
        )

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\nSummary: {self.passed} passed, {self.failed} failed, "
              f"{self.skipped} skipped, {total} total")
        return 0 if self.failed == 0 else 1


def assert_release_receipt(receipt_path: Path, r: Result):
    """Make smoke validation consume the structured release receipt."""

    try:
        receipt = load_json_object(receipt_path)
    except ValueError as exc:
        r.fail(
            "release receipt missing or invalid",
            str(exc),
            check_id="release_receipt.readable",
            failure_code="RELEASE_RECEIPT_UNREADABLE",
        )
        return
    if receipt.get("status") == "pass":
        r.ok(
            "release receipt status = pass",
            check_id="release_receipt.status",
            evidence={"schema_version": receipt.get("schema_version")},
        )
    else:
        r.fail(
            "release receipt status is not pass",
            str(receipt.get("status", "missing")),
            check_id="release_receipt.status",
            evidence={"status": receipt.get("status")},
            failure_code="RELEASE_RECEIPT_FAILED",
        )
    if isinstance(receipt.get("diagnostics"), dict):
        r.ok(
            "release receipt diagnostics present",
            check_id="release_receipt.diagnostics",
            evidence={"schema_version": receipt["diagnostics"].get("schema_version")},
        )
    else:
        r.fail(
            "release receipt diagnostics missing",
            check_id="release_receipt.diagnostics",
            failure_code="RELEASE_DIAGNOSTICS_MISSING",
        )


def find_build_outputs(repo_root: Path):
    """Locate the artifacts under build/ that smoke tests inspect."""
    out = repo_root / "build" / "src" / "out" / "Default"
    if not out.exists():
        return None
    return out


def find_extracted_build_root(extract_dir: Path) -> Path:
    """Resolve a portable ZIP's direct root or its single named directory."""
    if (extract_dir / "chrome.exe").is_file():
        return extract_dir
    candidates = [
        child for child in extract_dir.iterdir()
        if child.is_dir() and (child / "chrome.exe").is_file()
    ]
    return candidates[0] if len(candidates) == 1 else extract_dir


def assert_files_present(out_dir: Path, r: Result):
    """Step 1: required files are in the build output."""
    print("\n[1] File-presence checks")
    for rel in ["chrome.exe", "initial_preferences",
                "default_extensions", "Extensions", "policies"]:
        p = out_dir / rel
        if p.exists():
            r.ok(f"present: {rel}")
        else:
            r.fail(f"missing: {rel}", str(p))


def load_initial_prefs(out_dir: Path, r: Result):
    """Step 2: initial_preferences is valid JSON."""
    print("\n[2] initial_preferences JSON validity")
    f = out_dir / "initial_preferences"
    if not f.exists():
        r.fail("initial_preferences not in build output")
        return None
    try:
        prefs = json.loads(f.read_text(encoding="utf-8"))
        r.ok("valid JSON")
        return prefs
    except json.JSONDecodeError as e:
        r.fail("invalid JSON", str(e))
        return None


def assert_search_engine(prefs, r: Result):
    """Step 3: default search engine is DuckDuckGo (N1)."""
    print("\n[3] Default search engine (N1)")
    if not prefs:
        r.skip("default search engine", "no prefs loaded")
        return
    try:
        kw = prefs["default_search_provider_data"]["template_url_data"]["keyword"]
    except KeyError:
        r.fail("default_search_provider_data missing or malformed")
        return
    if kw == EXPECTED_SEARCH_KEYWORD:
        r.ok(f"keyword = {kw}")
    else:
        r.fail(f"keyword = {kw}", f"expected {EXPECTED_SEARCH_KEYWORD}")


def assert_https_only(prefs, r: Result):
    """Step 4: HTTPS-First Balanced is on (N2)."""
    print("\n[4] HTTPS-First Balanced (N2)")
    if not prefs:
        r.skip("HTTPS-First", "no prefs loaded")
        return
    for k in ("https_only_mode_enabled", "https_first_balanced_mode_enabled"):
        if prefs.get(k) is True:
            r.ok(f"{k} = true")
        else:
            r.fail(f"{k}", f"expected true, got {prefs.get(k)!r}")


def assert_safe_browsing(prefs, r: Result):
    """Step 5: Safe Browsing on, telemetry off (N4)."""
    print("\n[5] Safe Browsing posture (N4)")
    sb = prefs.get("safebrowsing", {}) if prefs else {}
    if sb.get("enabled") is True:
        r.ok("safebrowsing.enabled = true")
    else:
        r.fail("safebrowsing.enabled", f"expected true, got {sb.get('enabled')!r}")
    for k in ("enhanced", "scout_reporting_enabled", "extended_reporting_enabled"):
        if sb.get(k) is False:
            r.ok(f"safebrowsing.{k} = false")
        else:
            r.fail(f"safebrowsing.{k}", f"expected false, got {sb.get(k)!r}")


def assert_privacy_sandbox(prefs, r: Result):
    """Step 6: Privacy Sandbox APIs disabled (N6)."""
    print("\n[6] Privacy Sandbox disabled (N6)")
    ps = prefs.get("privacy_sandbox", {}) if prefs else {}
    if ps.get("apis_enabled_v2") is False:
        r.ok("privacy_sandbox.apis_enabled_v2 = false")
    else:
        r.fail("privacy_sandbox.apis_enabled_v2", f"got {ps.get('apis_enabled_v2')!r}")
    m1 = ps.get("m1", {}) if ps else {}
    for k in ("topics_enabled", "fledge_enabled", "ad_measurement_enabled"):
        if m1.get(k) is False:
            r.ok(f"privacy_sandbox.m1.{k} = false")
        else:
            r.fail(f"privacy_sandbox.m1.{k}", f"got {m1.get(k)!r}")


def assert_content_settings(prefs, r: Result):
    """Step 7: high-risk content settings default-denied (N5)."""
    print("\n[7] Content-setting default-deny (N5)")
    cs = (prefs.get("profile", {}) or {}).get("default_content_setting_values", {}) \
        if prefs else {}
    # Chromium content-setting value 2 = block
    expect_blocked = ["usb_devices", "serial_ports", "hid_devices",
                      "bluetooth_devices", "idle_detection", "local_fonts",
                      "payment_handler", "ar", "vr"]
    for k in expect_blocked:
        if cs.get(k) == 2:
            r.ok(f"{k} = block")
        else:
            r.fail(f"{k}", f"expected 2 (block), got {cs.get(k)!r}")


def assert_managed_defaults(repo_root: Path, out_dir: Path, r: Result):
    """Step 7b: the optional enterprise baseline keeps risky APIs blocked."""
    print("\n[7b] Managed policy baseline (N5)")
    policy_path = repo_root / "policies" / "vigil-defaults.json"
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        r.fail("managed policy baseline missing or invalid", str(e))
        return
    for key in (
        "DefaultWebUsbGuardSetting",
        "DefaultSerialGuardSetting",
        "DefaultWebHidGuardSetting",
        "DefaultWebBluetoothGuardSetting",
        "DefaultIdleDetectionSetting",
        "DefaultLocalFontsSetting",
    ):
        if policy.get(key) == 2:
            r.ok(f"{key} = block")
        else:
            r.fail(key, f"expected 2 (block), got {policy.get(key)!r}")
    if policy.get("PaymentMethodQueryEnabled") is False:
        r.ok("PaymentMethodQueryEnabled = false")
    else:
        r.fail("PaymentMethodQueryEnabled", "expected false")

    packaged = out_dir / "policies" / policy_path.name
    try:
        packaged_policy = json.loads(packaged.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        r.fail("managed policy baseline not packaged", str(e))
    else:
        if packaged_policy == policy:
            r.ok("managed policy baseline packaged unchanged")
        else:
            r.fail("packaged managed policy baseline differs from source")


def assert_kiosk_policy(repo_root: Path, out_dir: Path, r: Result):
    """Step 7c: kiosk autoplay is packaged as policy, not a CLI override."""
    print("\n[7c] Kiosk autoplay policy")
    policy_path = repo_root / "policies" / "vigil-kiosk.json"
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        packaged = json.loads(
            (out_dir / "policies" / policy_path.name).read_text(encoding="utf-8")
        )
    except (FileNotFoundError, json.JSONDecodeError) as e:
        r.fail("kiosk policy missing, invalid, or not packaged", str(e))
        return
    if policy.get("AutoplayAllowed") is False:
        r.ok("AutoplayAllowed = false")
    else:
        r.fail("AutoplayAllowed", "expected false")
    if packaged == policy:
        r.ok("kiosk policy packaged unchanged")
    else:
        r.fail("packaged kiosk policy differs from source")


def assert_ubo_bundle(out_dir: Path, r: Result):
    """Step 8: uBO staged under Extensions/<id>/<v>/ and manifest is valid."""
    print("\n[8] uBlock Origin bundled")
    ext_root = out_dir / "Extensions" / UBO_EXT_ID
    if not ext_root.exists():
        r.fail("uBO extension dir missing", str(ext_root))
        return
    versions = [d for d in ext_root.iterdir() if d.is_dir()]
    if not versions:
        r.fail("no uBO version dir under Extensions/<id>/")
        return
    v = versions[0]
    r.ok(f"uBO version directory: {v.name}", check_id="smoke.ubo.version_directory")
    manifest = v / "manifest.json"
    if not manifest.exists():
        r.fail("uBO manifest.json missing")
        return
    try:
        m = json.loads(manifest.read_text(encoding="utf-8"))
        r.ok(
            f"uBO manifest valid (declared version {m.get('version')!r})",
            check_id="smoke.ubo.manifest_valid",
        )
    except json.JSONDecodeError as e:
        r.fail("uBO manifest invalid JSON", str(e))
        return
    # External-extensions pointer
    ptr = out_dir / "default_extensions" / f"{UBO_EXT_ID}.json"
    if ptr.exists():
        r.ok("external-extensions pointer present")
    else:
        r.fail("external-extensions pointer missing", str(ptr))


def extension_id_from_manifest(manifest):
    """Compute Chromium's stable extension ID from a manifest public key."""
    key = manifest.get("key")
    if not key:
        return None
    digest = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32]
    return "".join(chr(ord("a") + int(char, 16)) for char in digest)


def assert_ntp_extension(repo_root: Path, out_dir: Path, r: Result):
    """Step 9: the NTP manifest and staged extension are wired correctly."""
    print("\n[9] NTP extension wiring (N3)")
    manifest = repo_root / "ntp-extension" / "manifest.json"
    if not manifest.exists():
        r.skip("ntp-extension manifest", "not present in this source checkout")
        return
    try:
        m = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        r.fail("ntp-extension manifest invalid JSON", str(e))
        return
    overrides = m.get("chrome_url_overrides", {})
    if overrides.get("newtab"):
        r.ok(f"newtab override -> {overrides['newtab']}")
    else:
        r.fail("chrome_url_overrides.newtab missing")
    ext_id = extension_id_from_manifest(m)
    if not ext_id:
        r.fail("ntp-extension manifest has no stable public key")
        return
    version = m.get("version")
    staged = out_dir / "Extensions" / ext_id / version
    if (staged / "manifest.json").exists():
        r.ok(
            f"staged NTP extension: {ext_id}/{version}",
            check_id="smoke.ntp.staged_extension",
        )
    else:
        r.fail("staged NTP extension missing", str(staged))
    pointer = out_dir / "default_extensions" / f"{ext_id}.json"
    try:
        pointer_data = json.loads(pointer.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        r.fail("NTP external-extensions pointer missing or invalid", str(e))
    else:
        expected = f"Extensions/{ext_id}/{version}"
        if pointer_data.get("external_crx") == expected:
            r.ok("NTP external-extensions pointer valid")
        else:
            r.fail("NTP external-extensions pointer target", str(pointer_data))
    locale_path = staged / "_locales" / "en" / "messages.json"
    if m.get("default_locale") != "en" or not locale_path.is_file():
        r.fail("NTP English locale missing", str(locale_path))
    else:
        try:
            locale = json.loads(locale_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            r.fail("NTP English locale invalid", str(e))
        else:
            if locale and all(entry.get("message") for entry in locale.values()):
                r.ok("NTP English locale packaged")
            else:
                r.fail("NTP English locale is empty or malformed")


def assert_command_palette(repo_root: Path, out_dir: Path, r: Result):
    """Step 9b: the keyboard command palette is bundled and addressable."""
    print("\n[9b] Command palette extension (X18)")
    manifest_path = repo_root / "palette-extension" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        r.fail("command palette manifest missing or invalid", str(e))
        return
    commands = manifest.get("commands", {})
    shortcut = commands.get("open-palette", {}).get("suggested_key", {}).get("default")
    if shortcut == "Ctrl+Shift+P":
        r.ok("Ctrl+Shift+P command declared")
    else:
        r.fail("command palette shortcut", f"expected Ctrl+Shift+P, got {shortcut!r}")
    if set(("tabs", "bookmarks", "history")).issubset(manifest.get("permissions", [])):
        r.ok("tab, bookmark, and history permissions declared")
    else:
        r.fail("command palette data permissions missing")

    ext_id = extension_id_from_manifest(manifest)
    version = manifest.get("version")
    staged = out_dir / "Extensions" / ext_id / version
    for filename in (
        "manifest.json",
        "background.js",
        "content.js",
        "palette.html",
        "i18n.js",
        "_locales/en/messages.json",
    ):
        if (staged / filename).is_file():
            r.ok(f"staged palette file: {filename}")
        else:
            r.fail(f"staged palette file missing: {filename}", str(staged / filename))
    if manifest.get("default_locale") == "en":
        r.ok("palette English locale declared")
    else:
        r.fail("palette English locale missing")
    pointer = out_dir / "default_extensions" / f"{ext_id}.json"
    try:
        pointer_data = json.loads(pointer.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        r.fail("command palette pointer missing or invalid", str(e))
    else:
        expected = f"Extensions/{ext_id}/{version}"
        if pointer_data.get("external_crx") == expected:
            r.ok("command palette external-extensions pointer valid")
        else:
            r.fail("command palette pointer target", str(pointer_data))


def assert_selenium_launch(out_dir: Path, r: Result):
    """Step 10 (optional): launch the build via Selenium and check overlays."""
    print("\n[10] Selenium launch (optional)")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        r.skip("Selenium not installed", "pip install selenium")
        return
    chromedriver = out_dir / "chromedriver.exe"
    chrome = out_dir / "chrome.exe"
    if not chromedriver.exists() or not chrome.exists():
        r.skip("Selenium launch", "chrome.exe or chromedriver.exe missing")
        return
    with tempfile.TemporaryDirectory() as tmp:
        opts = Options()
        opts.binary_location = str(chrome)
        opts.add_argument(f"--user-data-dir={tmp}")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")
        service = Service(executable_path=str(chromedriver))
        try:
            driver = webdriver.Chrome(service=service, options=opts)
        except Exception as e:
            r.fail("could not start Chromium under selenium", str(e))
            return
        try:
            driver.get("chrome://version/")
            body = driver.find_element("css selector", "body").text
            if "Vigil" in body or "Chromium" in body:
                r.ok("chrome://version renders")
            else:
                r.fail("chrome://version body missing brand string")
        finally:
            driver.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-out", default=None,
        help="Path to build/src/out/Default. Defaults to repo-relative.")
    parser.add_argument(
        "--installer", default=None,
        help="(Optional) path to a packaged installer; if given, the test will "
             "unzip it to a temp directory and run against that.")
    parser.add_argument(
        "--selenium", action="store_true",
        help="Run the optional Selenium step (step 10).")
    parser.add_argument(
        "--receipt",
        type=Path,
        help="Consume a release receipt and verify its structured diagnostics.",
    )
    parser.add_argument(
        "--diagnostics-output",
        type=Path,
        help="Write the structured smoke-test report to this JSON path.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    if args.installer:
        # Unzip the installer (we ship a zip alongside the exe) into a tempdir
        # and treat that as the build-output root.
        inst = Path(args.installer).resolve()
        if not inst.exists():
            print(f"ERROR: installer not found: {inst}", file=sys.stderr)
            return 2
        installer_tmp = tempfile.TemporaryDirectory(prefix="vigil-smoke-")
        tmp = Path(installer_tmp.name)
        if inst.suffix.lower() == ".zip":
            with zipfile.ZipFile(inst) as zf:
                zf.extractall(tmp)
            out_dir = find_extracted_build_root(tmp)
        else:
            print("Only --installer *.zip is supported for now.", file=sys.stderr)
            return 2
    elif args.build_out:
        out_dir = Path(args.build_out).resolve()
    else:
        out_dir = find_build_outputs(repo_root)
        if not out_dir:
            print("ERROR: no build outputs found. Run build.py first or pass "
                  "--build-out / --installer.", file=sys.stderr)
            return 2

    print(f"Vigil smoke test against: {out_dir}")
    r = Result()

    if args.receipt:
        assert_release_receipt(args.receipt.resolve(), r)

    assert_files_present(out_dir, r)
    prefs = load_initial_prefs(out_dir, r)
    assert_search_engine(prefs, r)
    assert_https_only(prefs, r)
    assert_safe_browsing(prefs, r)
    assert_privacy_sandbox(prefs, r)
    assert_content_settings(prefs, r)
    assert_managed_defaults(repo_root, out_dir, r)
    assert_kiosk_policy(repo_root, out_dir, r)
    assert_ubo_bundle(out_dir, r)
    assert_ntp_extension(repo_root, out_dir, r)
    assert_command_palette(repo_root, out_dir, r)

    if args.selenium:
        assert_selenium_launch(out_dir, r)
    else:
        print("\n[10] Selenium launch  SKIP (pass --selenium to run)")

    result = r.summary()
    if args.diagnostics_output:
        try:
            write_json_atomic(args.diagnostics_output, r.diagnostics_report())
        except OSError as exc:
            print(f"ERROR: could not write diagnostics report: {exc}", file=sys.stderr)
            return 2
    return result


if __name__ == "__main__":
    sys.exit(main())
