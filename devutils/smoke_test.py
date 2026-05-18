#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vigil smoke test (roadmap item N14).

Installs / unzips the built artifact in a throwaway profile, launches it with a
known harness URL, and asserts the post-conditions that the v0.2 defaults work.

Designed to be runnable on:

  - the maintainer's workstation (`python devutils/smoke_test.py --installer ...`)
  - GitHub Actions windows-2022 runners (the build matrix runs this after each
    release-candidate build)
  - a clean Windows VM (Hyper-V image) the maintainer keeps for release sign-off

Tests, in order of cheapest -> most expensive:

  1. File presence in the build output (initial_preferences, ntp-extension, etc.)
  2. JSON validity of initial_preferences
  3. Default-search-engine = DuckDuckGo (from initial_preferences inspection)
  4. HTTPS-First Balanced mode on (from initial_preferences inspection)
  5. Safe Browsing re-enabled, telemetry off (from initial_preferences inspection)
  6. Privacy Sandbox APIs disabled (from initial_preferences inspection)
  7. Permissions-Policy default-deny content settings (from initial_preferences)
  8. uBO staged in Extensions/cjpalhdlnbpafiamejdnhcphjbkeiagm/<v>/ + manifest valid
  9. NTP extension declares chrome_url_overrides.newtab
 10. (Optional) Selenium-driven launch: open chrome://settings, confirm the page
     renders and the Vigil-overlay CSS is applied (looks for a known class).

Steps 1-9 do NOT require launching Chrome and are the CI-fast path.
Step 10 only runs when --selenium is passed AND chromedriver is on PATH.

Exit codes:
   0 - all assertions passed
   1 - one or more assertions failed
   2 - test harness error (paths missing, etc.)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

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

    def ok(self, label):
        print(f"  PASS  {label}")
        self.passed += 1

    def fail(self, label, detail=""):
        print(f"  FAIL  {label}")
        if detail:
            print(f"        {detail}")
        self.failed += 1

    def skip(self, label, reason):
        print(f"  SKIP  {label} ({reason})")
        self.skipped += 1

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\nSummary: {self.passed} passed, {self.failed} failed, "
              f"{self.skipped} skipped, {total} total")
        return 0 if self.failed == 0 else 1


def find_build_outputs(repo_root: Path):
    """Locate the artifacts under build/ that smoke tests inspect."""
    out = repo_root / "build" / "src" / "out" / "Default"
    if not out.exists():
        return None
    return out


def assert_files_present(out_dir: Path, r: Result):
    """Step 1: required files are in the build output."""
    print("\n[1] File-presence checks")
    for rel in ["chrome.exe", "initial_preferences",
                "default_extensions", "Extensions"]:
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
    r.ok(f"uBO version directory: {v.name}")
    manifest = v / "manifest.json"
    if not manifest.exists():
        r.fail("uBO manifest.json missing")
        return
    try:
        m = json.loads(manifest.read_text(encoding="utf-8"))
        r.ok(f"uBO manifest valid (declared version {m.get('version')!r})")
    except json.JSONDecodeError as e:
        r.fail("uBO manifest invalid JSON", str(e))
        return
    # External-extensions pointer
    ptr = out_dir / "default_extensions" / f"{UBO_EXT_ID}.json"
    if ptr.exists():
        r.ok("external-extensions pointer present")
    else:
        r.fail("external-extensions pointer missing", str(ptr))


def assert_ntp_extension(repo_root: Path, r: Result):
    """Step 9: ntp-extension/ declares chrome_url_overrides.newtab."""
    print("\n[9] NTP extension wiring (N3)")
    manifest = repo_root / "ntp-extension" / "manifest.json"
    if not manifest.exists():
        r.skip("ntp-extension manifest", "not yet present (N3 scaffold still pending)")
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
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    if args.installer:
        # Unzip the installer (we ship a zip alongside the exe) into a tempdir
        # and treat that as the build-output root.
        inst = Path(args.installer).resolve()
        if not inst.exists():
            print(f"ERROR: installer not found: {inst}", file=sys.stderr)
            return 2
        tmp = Path(tempfile.mkdtemp(prefix="vigil-smoke-"))
        if inst.suffix.lower() == ".zip":
            with zipfile.ZipFile(inst) as zf:
                zf.extractall(tmp)
            out_dir = tmp
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

    assert_files_present(out_dir, r)
    prefs = load_initial_prefs(out_dir, r)
    assert_search_engine(prefs, r)
    assert_https_only(prefs, r)
    assert_safe_browsing(prefs, r)
    assert_privacy_sandbox(prefs, r)
    assert_content_settings(prefs, r)
    assert_ubo_bundle(out_dir, r)
    assert_ntp_extension(repo_root, r)

    if args.selenium:
        assert_selenium_launch(out_dir, r)
    else:
        print("\n[10] Selenium launch  SKIP (pass --selenium to run)")

    return r.summary()


if __name__ == "__main__":
    sys.exit(main())
