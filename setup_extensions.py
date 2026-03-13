#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Downloads and installs uBlock Origin into the ungoogled-chromium build output
so it is pre-installed on first launch.

Uses Chromium's external extensions mechanism (file-based JSON provider).
Run this AFTER build.py completes but BEFORE package.py.
"""

import io
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

# uBlock Origin extension ID (Chrome Web Store ID)
UBLOCK_EXTENSION_ID = "cjpalhdlnbpafiamejdnhcphjbkeiagm"

# gorhill/uBlock is the official repo - releases include .chromium.zip builds
UBLOCK_RELEASES_API = "https://api.github.com/repos/gorhill/uBlock/releases/latest"


def get_ublock_download_url():
    """Get the latest uBlock Origin Chromium release URL from GitHub."""
    print("  Querying GitHub for latest uBlock Origin release...")
    try:
        req = urllib.request.Request(
            UBLOCK_RELEASES_API,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "ungoogled-chromium-builder"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            version = data["tag_name"]

            # Look for the Chromium-specific zip (e.g., uBlock0_1.62.0.chromium.zip)
            for asset in data.get("assets", []):
                name = asset["name"].lower()
                if "chromium" in name and name.endswith(".zip"):
                    return asset["browser_download_url"], version

            # Fallback: any zip that isn't firefox/thunderbird/npm
            for asset in data.get("assets", []):
                name = asset["name"].lower()
                if name.endswith(".zip") and "firefox" not in name and "thunderbird" not in name and "npm" not in name:
                    return asset["browser_download_url"], version

    except Exception as e:
        print(f"  ERROR: Could not query GitHub API: {e}")

    return None, None


def download_and_extract_ublock(chrome_dir):
    """Download uBlock Origin and install it as an unpacked external extension."""
    print("Setting up uBlock Origin...")

    url, version = get_ublock_download_url()
    if not url:
        print("  ERROR: Could not find uBlock Origin release.")
        print("  You can manually download from: https://github.com/gorhill/uBlock/releases")
        return False

    print(f"  Downloading uBlock Origin {version}...")
    print(f"  URL: {url}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ungoogled-chromium-builder"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            zip_data = resp.read()
    except Exception as e:
        print(f"  ERROR: Download failed: {e}")
        return False

    # Temporary extraction to read manifest
    print("  Extracting...")
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_data))
    except Exception as e:
        print(f"  ERROR: Invalid zip file: {e}")
        return False

    # Detect if files are nested in a subdirectory
    names = zf.namelist()
    prefix = ""
    if names:
        first_parts = set()
        for n in names:
            parts = n.split("/")
            if len(parts) > 1:
                first_parts.add(parts[0])
        if len(first_parts) == 1:
            potential = first_parts.pop() + "/"
            if all(n.startswith(potential) or n.rstrip("/") + "/" == potential for n in names):
                prefix = potential

    # Read manifest.json to get the actual version
    manifest_path = prefix + "manifest.json"
    try:
        manifest_data = json.loads(zf.read(manifest_path).decode("utf-8"))
        actual_version = manifest_data.get("version", version.lstrip("v"))
    except Exception:
        actual_version = version.lstrip("v")

    # Extract to Extensions/<id>/<version>/
    ext_dir = chrome_dir / "Extensions" / UBLOCK_EXTENSION_ID / actual_version
    if ext_dir.exists():
        shutil.rmtree(ext_dir)
    ext_dir.mkdir(parents=True, exist_ok=True)

    for member in zf.infolist():
        if member.is_dir():
            continue
        rel_path = member.filename
        if prefix and rel_path.startswith(prefix):
            rel_path = rel_path[len(prefix):]
        if not rel_path:
            continue
        target = ext_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member) as src, open(target, "wb") as dst:
            dst.write(src.read())

    zf.close()

    # Create the external extension preference JSON
    # Chromium's ExternalPrefExtensionLoader reads JSON files from a known directory
    # For Windows portable builds, we use the "default_extensions" directory next to chrome.exe
    ext_json_dir = chrome_dir / "default_extensions"
    ext_json_dir.mkdir(parents=True, exist_ok=True)

    ext_json = {
        "external_crx": f"Extensions/{UBLOCK_EXTENSION_ID}/{actual_version}",
        "external_version": actual_version
    }

    json_path = ext_json_dir / f"{UBLOCK_EXTENSION_ID}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ext_json, f, indent=2)

    print(f"  uBlock Origin {actual_version} installed successfully!")
    print(f"  Extension dir: {ext_dir}")
    print(f"  JSON manifest: {json_path}")
    return True


def main():
    root_dir = Path(__file__).resolve().parent
    chrome_dir = root_dir / "build" / "src" / "out" / "Default"

    if not chrome_dir.exists():
        print(f"ERROR: Build output directory not found: {chrome_dir}")
        print("Run build.py first, then run this script before package.py.")
        sys.exit(1)

    success = download_and_extract_ublock(chrome_dir)
    if success:
        print("\nExtension setup complete!")
        print("Run package.py to create the final package with uBlock Origin included.")
    else:
        print("\nExtension setup had errors. You can install uBlock Origin manually later.")
        sys.exit(1)


if __name__ == "__main__":
    main()
