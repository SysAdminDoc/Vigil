#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stage the Vigil NTP extension into the build output so it loads as
chrome://newtab on first run. Roadmap item N3.

Pipeline (called from package.py after setup_extensions.py):

  1. Locate ntp-extension/ at the repo root.
  2. Determine the extension's stable ID from the public `key` field in
     manifest.json. The public key is committed so packaging never needs to
     launch a browser or generate a CRX.
  3. Stage the unpacked extension into
        build/src/out/Default/Extensions/<id>/<version>/
     mirroring the layout setup_extensions.py uses for uBO.
  4. Write the external-extensions pointer JSON to
        build/src/out/Default/default_extensions/<id>.json

The same script can be invoked manually:

    python tools/install_ntp_extension.py
    python tools/install_ntp_extension.py --build-out path/to/Default

A note on key management:

  The public half of the extension keypair is committed inside manifest.json,
  which is sufficient for Chromium to compute a stable ID. Vigil ships this
  extension unpacked inside the installer and never signs a CRX from the key.
"""

import argparse
import base64
import hashlib
import json
import shutil
import sys
from pathlib import Path

from atomic_stage import atomic_copy_tree

REPO_ROOT = Path(__file__).resolve().parent.parent
NTP_DIR = REPO_ROOT / "ntp-extension"
DEFAULT_BUILD_OUT = REPO_ROOT / "build" / "src" / "out" / "Default"


def chromium_extension_id_from_public_key_b64(b64_key: str) -> str:
    """
    Compute the Chromium extension ID for a base64-encoded DER public key.

    Chromium hashes the DER bytes (NOT the base64) with SHA-256, then maps
    the first 32 hex characters to a-p ('a' + int(hex_char, 16)).
    """
    der = base64.b64decode(b64_key)
    h = hashlib.sha256(der).hexdigest()[:32]
    return "".join(chr(ord("a") + int(c, 16)) for c in h)


def ensure_manifest_key(manifest_path: Path) -> str:
    """
    Ensure manifest.json has a `key` field (so the extension ID is stable).
    Returns the resulting extension ID.

    The key is deliberately required in source control. Generating a key by
    launching the browser during packaging would make builds depend on a GUI
    process and would make the extension ID change when the build environment
    changes.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pub_key = manifest.get("key")

    if pub_key:
        return chromium_extension_id_from_public_key_b64(pub_key)

    raise RuntimeError(
        "manifest.json must contain a stable public 'key' before packaging; "
        "refusing to generate one by launching a browser")


def stage_extension(ext_id: str, build_out: Path):
    """Copy ntp-extension/ to build_out/Extensions/<id>/<version>/."""
    manifest = json.loads((NTP_DIR / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    target = build_out / "Extensions" / ext_id / version
    atomic_copy_tree(
        NTP_DIR,
        target,
        ignore=shutil.ignore_patterns("*.pem", "*.crx"),
    )
    print(f"  Staged {NTP_DIR.name}/ -> Extensions/{ext_id}/{version}/")

    pointer_dir = build_out / "default_extensions"
    pointer_dir.mkdir(parents=True, exist_ok=True)
    pointer = pointer_dir / f"{ext_id}.json"
    pointer_data = json.dumps({
        "external_crx": f"Extensions/{ext_id}/{version}",
        "external_version": version
    }, indent=2) + "\n"
    pointer_stage = pointer.with_name(f".{pointer.name}.stage")
    pointer_stage.write_text(pointer_data, encoding="utf-8")
    try:
        pointer_stage.replace(pointer)
    finally:
        if pointer_stage.exists():
            pointer_stage.unlink()
    print(f"  Wrote external-extensions pointer: {pointer.relative_to(build_out)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-out", default=str(DEFAULT_BUILD_OUT),
        help="Path to build/src/out/Default (or wherever chrome.exe lives).")
    args = parser.parse_args()

    if not NTP_DIR.exists():
        print(f"ERROR: {NTP_DIR} not found. Did you delete ntp-extension/?",
              file=sys.stderr)
        return 2

    manifest_path = NTP_DIR / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} missing.", file=sys.stderr)
        return 2

    build_out = Path(args.build_out)
    print(f"Installing Vigil NTP extension into {build_out}")

    try:
        ext_id = ensure_manifest_key(manifest_path)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"  Extension ID: {ext_id}")

    if not build_out.exists():
        print(f"  (build output does not exist; ID baked but staging skipped: "
              f"{build_out})")
        return 0

    stage_extension(ext_id, build_out)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
