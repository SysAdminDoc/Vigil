#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Applies chromium_src overlays and custom assets to the Chromium source tree.

Brave-style overlay system: files in chromium_src/ mirror the Chromium source
tree structure and replace the corresponding files at build time.

Also installs the custom New Tab Page and applies branding from branding.json.
"""

import json
import os
import shutil
import sys
from pathlib import Path


def apply_chromium_src_overlays(root_dir, source_tree):
    """Copy files from chromium_src/ into the source tree, replacing originals."""
    overlay_dir = root_dir / 'chromium_src'
    if not overlay_dir.exists():
        print('  No chromium_src/ overlay directory found, skipping.')
        return 0

    count = 0
    for src_file in overlay_dir.rglob('*'):
        if src_file.is_dir():
            continue
        rel_path = src_file.relative_to(overlay_dir)
        dst_file = source_tree / rel_path

        # Back up original if it exists and hasn't been backed up yet
        backup = dst_file.with_suffix(dst_file.suffix + '.orig')
        if dst_file.exists() and not backup.exists():
            shutil.copy2(dst_file, backup)

        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        count += 1
        print(f'  Overlay: {rel_path}')

    return count


def install_ntp(root_dir, source_tree):
    """Install the custom New Tab Page into the build."""
    ntp_dir = root_dir / 'ntp'
    if not ntp_dir.exists():
        print('  No ntp/ directory found, skipping.')
        return

    # Install NTP HTML into the resources directory
    # Chromium serves chrome://newtab from compiled resources, but we can
    # override it via the local NTP mechanism or a custom flag.
    # For portability, we install it as a local file that gets served.
    ntp_target = source_tree / 'chrome' / 'browser' / 'resources' / 'new_tab_page_custom'
    ntp_target.mkdir(parents=True, exist_ok=True)

    for f in ntp_dir.rglob('*'):
        if f.is_dir():
            continue
        rel = f.relative_to(ntp_dir)
        dst = ntp_target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)
        print(f'  NTP asset: {rel}')


def install_icons(root_dir, source_tree):
    """Install Vigil icons into Chromium's branding directories."""
    icons_dir = root_dir / 'branding' / 'icons'
    if not icons_dir.exists():
        print('  No branding/icons/ directory found, skipping.')
        return

    # Chromium icon locations that need to be replaced
    icon_targets = {
        # Windows .ico file (taskbar, window icon, exe icon)
        'vigil.ico': [
            'chrome/app/theme/chromium/win/chromium.ico',
        ],
        # PNG product logos at various sizes
        'product_logo_16.png': [
            'chrome/app/theme/chromium/product_logo_16.png',
        ],
        'product_logo_24.png': [
            'chrome/app/theme/chromium/product_logo_24.png',
        ],
        'product_logo_32.png': [
            'chrome/app/theme/chromium/product_logo_32.png',
            'chrome/app/theme/chromium/win/chromium_search.ico',
        ],
        'product_logo_48.png': [
            'chrome/app/theme/chromium/product_logo_48.png',
        ],
        'product_logo_64.png': [
            'chrome/app/theme/chromium/product_logo_64.png',
        ],
        'product_logo_128.png': [
            'chrome/app/theme/chromium/product_logo_128.png',
        ],
        'product_logo_256.png': [
            'chrome/app/theme/chromium/product_logo_256.png',
        ],
    }

    count = 0
    for src_name, targets in icon_targets.items():
        src = icons_dir / src_name
        if not src.exists():
            continue
        for target_rel in targets:
            dst = source_tree / target_rel
            if dst.exists():
                backup = dst.with_suffix(dst.suffix + '.orig')
                if not backup.exists():
                    shutil.copy2(dst, backup)
                shutil.copy2(src, dst)
                count += 1
                print(f'  Icon: {src_name} -> {target_rel}')
            else:
                # Target doesn't exist yet; create parent and copy
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                count += 1
                print(f'  Icon (new): {src_name} -> {target_rel}')

    print(f'  Replaced {count} icon file(s).')


def apply_branding(root_dir, source_tree):
    """Apply branding from branding.json to source tree files."""
    branding_file = root_dir / 'branding.json'
    if not branding_file.exists():
        print('  No branding.json found, skipping.')
        return

    with open(branding_file, 'r', encoding='utf-8') as f:
        branding = json.load(f)

    browser_name = branding.get('browser_name', 'Chromium')
    company = branding.get('company_name', '')

    if browser_name == 'Chromium':
        print('  Using default Chromium branding (set browser_name in branding.json to customize).')
        return

    # Apply BRANDING file override
    branding_path = source_tree / 'chrome' / 'app' / 'theme' / 'chromium' / 'BRANDING'
    if branding_path.exists():
        content = branding_path.read_text(encoding='utf-8')
        content = content.replace('Chromium', browser_name)
        if company:
            content = content.replace('The Chromium Authors', company)
        branding_path.write_text(content, encoding='utf-8')
        print(f'  Branded: {branding_path.relative_to(source_tree)}')

    # Replace browser name in string resources
    string_files = [
        'chrome/app/chromium_strings.grd',
        'chrome/app/generated_resources.grd',
    ]
    for rel_path in string_files:
        fpath = source_tree / rel_path
        if fpath.exists():
            content = fpath.read_text(encoding='utf-8')
            if 'Chromium' in content:
                content = content.replace('Chromium', browser_name)
                fpath.write_text(content, encoding='utf-8')
                print(f'  Strings: {rel_path}')

    print(f'  Branding applied: {browser_name} by {company}')


def main():
    root_dir = Path(__file__).resolve().parent
    source_tree = root_dir / 'build' / 'src'

    if not source_tree.exists():
        print('ERROR: Source tree not found. Run build.py first.')
        sys.exit(1)

    print('Applying overlays...')
    count = apply_chromium_src_overlays(root_dir, source_tree)
    print(f'  Applied {count} overlay file(s).')

    print('Installing custom NTP...')
    install_ntp(root_dir, source_tree)

    print('Installing icons...')
    install_icons(root_dir, source_tree)

    print('Applying branding...')
    apply_branding(root_dir, source_tree)

    print('Overlay application complete.')


if __name__ == '__main__':
    main()
