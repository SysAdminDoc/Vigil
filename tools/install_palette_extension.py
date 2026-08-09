#!/usr/bin/env python3
"""Stage the bundled Vigil command-palette extension in a build output."""

import argparse
import base64
import hashlib
import json
import shutil
from pathlib import Path

from atomic_stage import atomic_copy_tree

REPO_ROOT = Path(__file__).resolve().parent.parent
PALETTE_DIR = REPO_ROOT / "palette-extension"
DEFAULT_BUILD_OUT = REPO_ROOT / "build" / "src" / "out" / "Default"
EXPECTED_ID = "cbcaldcobhchonhfdpkebccamicoiobd"


def extension_id(manifest):
    """Return Chromium's stable extension ID from the public key."""
    key = manifest.get("key")
    if not key:
        raise RuntimeError("palette manifest must contain a stable public key")
    digest = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32]
    return "".join(chr(ord("a") + int(char, 16)) for char in digest)


def stage(build_out):
    manifest_path = PALETTE_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ext_id = extension_id(manifest)
    if ext_id != EXPECTED_ID:
        raise RuntimeError(f"palette extension ID changed: {ext_id}")
    version = manifest["version"]
    target = build_out / "Extensions" / ext_id / version
    atomic_copy_tree(
        PALETTE_DIR,
        target,
        ignore=shutil.ignore_patterns("*.crx", "*.pem"),
    )

    pointer_dir = build_out / "default_extensions"
    pointer_dir.mkdir(parents=True, exist_ok=True)
    pointer = pointer_dir / f"{ext_id}.json"
    pointer_data = json.dumps({
        "external_crx": f"Extensions/{ext_id}/{version}",
        "external_version": version,
    }, indent=2) + "\n"
    pointer_stage = pointer.with_name(f".{pointer.name}.stage")
    pointer_stage.write_text(pointer_data, encoding="utf-8")
    try:
        pointer_stage.replace(pointer)
    finally:
        if pointer_stage.exists():
            pointer_stage.unlink()
    print(f"Staged command palette: Extensions/{ext_id}/{version}/")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-out", default=str(DEFAULT_BUILD_OUT))
    args = parser.parse_args()
    build_out = Path(args.build_out)
    if not PALETTE_DIR.exists():
        raise SystemExit(f"Missing extension source: {PALETTE_DIR}")
    if build_out.exists():
        stage(build_out)
    else:
        print(f"Build output does not exist; staging skipped: {build_out}")


if __name__ == "__main__":
    main()
