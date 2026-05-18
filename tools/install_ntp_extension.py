#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stage the Vigil NTP extension into the build output so it loads as
chrome://newtab on first run. Roadmap item N3.

Pipeline (called from package.py after setup_extensions.py):

  1. Locate ntp-extension/ at the repo root.
  2. Determine the extension's stable ID:
       - If `key` field exists in manifest.json, derive ID from it.
       - Otherwise, run `chrome.exe --pack-extension=ntp-extension` against
         the freshly-built chrome.exe; this generates ntp-extension/key.pem
         AND a .crx alongside. We then read the public key from the .crx
         and patch it into the manifest as the `key` field so the ID becomes
         stable across all future packagings.
  3. Stage the unpacked extension into
        build/src/out/Default/Extensions/<id>/<version>/
     mirroring the layout setup_extensions.py uses for uBO.
  4. Write the external-extensions pointer JSON to
        build/src/out/Default/default_extensions/<id>.json

The same script can be invoked manually:

    python tools/install_ntp_extension.py
    python tools/install_ntp_extension.py --build-out path/to/Default

A note on key management:

  The "private" half of the keypair (ntp-extension/key.pem) is **not** committed
  to the repository. The public half is committed inside manifest.json once it's
  baked in, which is sufficient for Chromium to compute a stable extension ID.
  We do not sign CRX updates from this private key (the extension is shipped
  unpacked inside the installer), so its only purpose is one-time ID stability.
  Treat it as a build-environment artifact and regenerate freely if lost.
"""

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

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


def ensure_manifest_key(manifest_path: Path, chrome_exe: Path) -> str:
    """
    Ensure manifest.json has a `key` field (so the extension ID is stable).
    Returns the resulting extension ID.

    If `key` is missing AND chrome.exe is available, run
        chrome.exe --pack-extension=<dir>
    to generate a private key file (`<dir>/../<dir>.pem`) and a .crx alongside;
    extract the public key from the .crx header and patch it into manifest.json.

    Raises if neither is possible.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pub_key = manifest.get("key")

    if pub_key:
        return chromium_extension_id_from_public_key_b64(pub_key)

    if not chrome_exe or not chrome_exe.exists():
        raise RuntimeError(
            "manifest.json has no 'key' field and chrome.exe was not provided. "
            "Run with --chrome-exe pointing to the freshly-built chrome.exe so the "
            "extension can be packed once to bake in a stable key.")

    print(f"  Packing {NTP_DIR.name}/ once via chrome.exe to generate a key...")
    pem_path = NTP_DIR.with_suffix(".pem")
    crx_path = NTP_DIR.with_suffix(".crx")
    # Remove any previous output
    for p in (pem_path, crx_path):
        if p.exists():
            p.unlink()
    subprocess.run(
        [str(chrome_exe), f"--pack-extension={NTP_DIR}", "--no-sandbox"],
        check=True)
    if not crx_path.exists():
        raise RuntimeError(f"chrome.exe did not produce {crx_path}")

    pub_key = _extract_pubkey_from_crx(crx_path)
    manifest["key"] = pub_key
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"  Wrote stable `key` into {manifest_path.relative_to(REPO_ROOT)}")
    return chromium_extension_id_from_public_key_b64(pub_key)


def _extract_pubkey_from_crx(crx_path: Path) -> str:
    """
    Pull the base64-encoded public key out of a CRX3 file.

    CRX3 header layout (little-endian):
        magic (4 bytes) = b"Cr24"
        version (4 bytes) = 3
        header_len (4 bytes)
        header (protobuf, header_len bytes)

    Inside the protobuf header, the first PROOF (tag=2 for crx3, RSA proof)
    contains a SubjectPublicKeyInfo. Rather than implementing a protobuf parser
    here, we use chrome.exe's --pack-extension semantics: the .pem file written
    next to the dir contains the *private* RSA key in PKCS8 PEM. We need the
    public key. Without `cryptography` installed we fall back to a tiny pure-Python
    parse of the .pem -> public bits.

    For minimal-deps we just read the .pem and use the cryptography lib if
    available; otherwise raise with a clear install hint.
    """
    pem_path = crx_path.with_suffix(".pem")
    if not pem_path.exists():
        # Some Chrome versions write the .pem alongside the extension dir, not the .crx
        alt = NTP_DIR.with_suffix(".pem")
        if alt.exists():
            pem_path = alt
        else:
            raise RuntimeError(
                f"Could not find generated private-key .pem next to {crx_path}")
    try:
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        raise RuntimeError(
            "Extracting the public key from the generated .pem requires the "
            "'cryptography' Python package. Install with: "
            "pip install cryptography")
    priv = serialization.load_pem_private_key(
        pem_path.read_bytes(), password=None)
    pub_der = priv.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    return base64.b64encode(pub_der).decode("ascii")


def stage_extension(ext_id: str, build_out: Path):
    """Copy ntp-extension/ to build_out/Extensions/<id>/<version>/."""
    manifest = json.loads((NTP_DIR / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    target = build_out / "Extensions" / ext_id / version
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    for src in NTP_DIR.rglob("*"):
        if src.is_dir():
            continue
        # Skip generated artifacts
        if src.suffix in (".pem", ".crx"):
            continue
        rel = src.relative_to(NTP_DIR)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f"  Staged {NTP_DIR.name}/ -> Extensions/{ext_id}/{version}/")

    pointer_dir = build_out / "default_extensions"
    pointer_dir.mkdir(parents=True, exist_ok=True)
    pointer = pointer_dir / f"{ext_id}.json"
    pointer.write_text(
        json.dumps({
            "external_crx": f"Extensions/{ext_id}/{version}",
            "external_version": version
        }, indent=2) + "\n", encoding="utf-8")
    print(f"  Wrote external-extensions pointer: {pointer.relative_to(build_out)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-out", default=str(DEFAULT_BUILD_OUT),
        help="Path to build/src/out/Default (or wherever chrome.exe lives).")
    parser.add_argument(
        "--chrome-exe", default=None,
        help="Path to chrome.exe used for one-time --pack-extension; defaults "
             "to <build-out>/chrome.exe.")
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
    chrome_exe = Path(args.chrome_exe) if args.chrome_exe \
                 else (build_out / "chrome.exe")

    print(f"Installing Vigil NTP extension into {build_out}")

    try:
        ext_id = ensure_manifest_key(manifest_path, chrome_exe)
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
