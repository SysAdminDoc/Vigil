#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
ungoogled-chromium packaging script for Microsoft Windows
"""

import sys
if sys.version_info.major < 3:
    raise RuntimeError('Python 3 is required for this script.')

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'ungoogled-chromium' / 'utils'))
import filescfg
from _common import ENCODING, get_chromium_version
sys.path.pop(0)

from devutils.build_preflight import assert_package_ready
from tools.atomic_stage import atomic_copy_file, atomic_copy_tree

def _get_release_revision():
    revision_path = Path(__file__).resolve().parent / 'ungoogled-chromium' / 'revision.txt'
    return revision_path.read_text(encoding=ENCODING).strip()

def _get_packaging_revision():
    revision_path = Path(__file__).resolve().parent / 'revision.txt'
    return revision_path.read_text(encoding=ENCODING).strip()


def _get_vigil_version(root_dir):
    manifest_path = root_dir / 'dist' / 'scoop' / 'vigil.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    version = manifest.get('version')
    if not version:
        raise RuntimeError(f'Missing Vigil version in {manifest_path}')
    return version

_cached_target_cpu = None

_CPU_ALIASES = {
    '64bit': 'x64',
    '32bit': 'x86',
    'arm': 'arm64',
    'x64': 'x64',
    'x86': 'x86',
    'arm64': 'arm64',
}
_FILESCFG_ARCH = {
    'x64': '64bit',
    'x86': '32bit',
    'arm64': 'arm',
}

def _get_target_cpu(build_outputs):
    global _cached_target_cpu
    if not _cached_target_cpu:
        with open(build_outputs / 'args.gn', 'r') as f:
            args_gn_text = f.read()
            for cpu in ('x64', 'x86', 'arm64'):
                if f'target_cpu="{cpu}"' in args_gn_text:
                    _cached_target_cpu = cpu
                    break
    assert _cached_target_cpu
    return _cached_target_cpu


def _get_wix_arch(target_cpu):
    return {
        'x64': 'x64',
        'x86': 'x86',
        'arm64': 'arm64',
    }[target_cpu]


def _normalize_cpu_arch(requested, target_cpu):
    """Normalize CLI aliases and reject packaging a different GN target."""
    if requested == 'auto':
        return target_cpu
    try:
        normalized = _CPU_ALIASES[requested]
    except KeyError as exc:
        raise RuntimeError(f'Unsupported CPU architecture: {requested}') from exc
    if normalized != target_cpu:
        raise RuntimeError(
            f'Package target mismatch: --cpu-arch {requested} selects {normalized}, '
            f'but args.gn selects {target_cpu}')
    return normalized


def _filescfg_cpu_arch(target_cpu):
    """Map a Chromium target name to the legacy FILES.cfg architecture tag."""
    try:
        return _FILESCFG_ARCH[target_cpu]
    except KeyError as exc:
        raise RuntimeError(f'No FILES.cfg mapping for CPU architecture: {target_cpu}') from exc


def _create_msi(root_dir, build_outputs, file_list, version, target_cpu):
    """Build a per-machine MSI from the same files as the portable archive."""
    wix = shutil.which('wix')
    if not wix:
        raise RuntimeError(
            'WiX Toolset 5 is required to create the Vigil MSI; '
            'install wix from https://wixtoolset.org/')

    msi_path = root_dir / 'build' / (
        f'vigil_{version}_installer_{target_cpu}.msi')
    # WiX selects its backend from the output suffix; retain .msi for the
    # temporary path while keeping it hidden and sibling to the final file.
    msi_stage = msi_path.with_name(f'.{msi_path.stem}.stage{msi_path.suffix}')
    wixpdb_path = msi_path.with_suffix('.wixpdb')
    wixpdb_stage = msi_stage.with_suffix('.wixpdb')
    wxs_path = root_dir / 'installer' / 'vigil.wxs'
    if not wxs_path.exists():
        raise RuntimeError(f'MSI authoring file is missing: {wxs_path}')

    with tempfile.TemporaryDirectory(prefix='vigil-msi-') as stage_name:
        stage = Path(stage_name)
        for rel_path in file_list:
            source = build_outputs / rel_path
            if not source.is_file():
                raise RuntimeError(f'MSI source file is missing: {source}')
            destination = stage / rel_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(source, destination)
            except OSError:
                shutil.copy2(source, destination)

        if msi_stage.exists():
            msi_stage.unlink()
        if wixpdb_stage.exists():
            wixpdb_stage.unlink()
        try:
            subprocess.run([
                wix, 'build',
                '-arch', _get_wix_arch(target_cpu),
                '-d', f'BuildOutput={stage}',
                '-d', f'ProductVersion={version}',
                '-d', f'Platform={target_cpu}',
                str(wxs_path),
                '-out', str(msi_stage),
            ], cwd=str(root_dir), check=True)
            os.replace(msi_stage, msi_path)
            if wixpdb_stage.exists():
                os.replace(wixpdb_stage, wixpdb_path)
            elif wixpdb_path.exists():
                # Do not leave a sidecar from an earlier package beside a new
                # MSI when WiX changes whether it emits a PDB.
                wixpdb_path.unlink()
        finally:
            if msi_stage.exists():
                msi_stage.unlink()
            if wixpdb_stage.exists():
                wixpdb_stage.unlink()
    print(f'Created MSI: {msi_path}')
    return msi_path

def main():
    """Entrypoint"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--cpu-arch',
        metavar='ARCH',
        default='auto',
        choices=('auto', 'x64', 'x86', 'arm64', '64bit', '32bit', 'arm'),
        help=('Filter build outputs by a target CPU. '
              'Use x64, x86, or arm64; 64bit/32bit/arm remain compatibility aliases. '
              'Default: infer from args.gn.'))
    parser.add_argument(
        '--offline',
        action='store_true',
        help='Refuse network access while staging pinned extension assets.')
    parser.add_argument(
        '--receipt',
        action='store_true',
        help='Write build/release-receipt.json after packaging.')
    args = parser.parse_args()

    build_outputs = Path('build/src/out/Default')
    root_dir = Path(__file__).resolve().parent
    assert_package_ready(root_dir, build_outputs, offline=args.offline)
    target_cpu = _get_target_cpu(build_outputs)
    normalized_cpu = _normalize_cpu_arch(args.cpu_arch, target_cpu)

    mini_installer = Path('build/ungoogled-chromium_{}-{}.{}_installer_{}.exe'.format(
        get_chromium_version(), _get_release_revision(),
        _get_packaging_revision(), _get_target_cpu(build_outputs)))
    atomic_copy_file(build_outputs / 'mini_installer.exe', mini_installer)

    timestamp = None
    try:
        with open('build/src/build/util/LASTCHANGE.committime', 'r') as ct:
            timestamp = int(ct.read())
    except FileNotFoundError:
        pass

    output = Path('build/ungoogled-chromium_{}-{}.{}_windows_{}.zip'.format(
        get_chromium_version(), _get_release_revision(),
        _get_packaging_revision(), _get_target_cpu(build_outputs)))

    # Copy initial_preferences next to chrome.exe for first-run defaults
    initial_prefs_src = root_dir / 'initial_preferences'
    initial_prefs_dst = build_outputs / 'initial_preferences'
    if initial_prefs_src.exists():
        atomic_copy_file(initial_prefs_src, initial_prefs_dst)
        print('Copied initial_preferences to build output')

    # Ship the administrator-facing managed-policy baselines with the
    # portable archive so deployments do not need a source checkout.
    policies_src = root_dir / 'policies'
    policies_dst = build_outputs / 'policies'
    if policies_src.exists():
        atomic_copy_tree(policies_src, policies_dst)
        print('Copied managed policy baselines to build output')

    # Run extension setup to download and bundle uBlock Origin
    setup_ext = root_dir / 'setup_extensions.py'
    if setup_ext.exists():
        print('Running extension setup...')
        setup_args = [sys.executable, str(setup_ext)]
        if args.offline:
            setup_args.append('--offline')
        subprocess.run(setup_args, cwd=str(root_dir), check=True)

    # Install the bundled Vigil NTP extension (roadmap N3).
    # This is the in-tree replacement for the legacy ntp/ html copy.
    install_ntp = root_dir / 'tools' / 'install_ntp_extension.py'
    if install_ntp.exists() and (root_dir / 'ntp-extension').exists():
        print('Installing Vigil NTP extension...')
        subprocess.run(
            [sys.executable, str(install_ntp),
             '--build-out', str(build_outputs)],
            cwd=str(root_dir), check=True)

    install_palette = root_dir / 'tools' / 'install_palette_extension.py'
    if install_palette.exists() and (root_dir / 'palette-extension').exists():
        print('Installing Vigil command palette extension...')
        subprocess.run(
            [sys.executable, str(install_palette),
             '--build-out', str(build_outputs)],
            cwd=str(root_dir), check=True)

    excluded_files = set([
        Path('mini_installer.exe'),
        Path('mini_installer_exe_version.rc'),
        Path('setup.exe'),
        Path('chrome.packed.7z'),
    ])
    files_generator = filescfg.filescfg_generator(
        Path('build/src/chrome/tools/build/win/FILES.cfg'),
        build_outputs, _filescfg_cpu_arch(normalized_cpu), excluded_files)

    # Copy custom NTP to build output
    ntp_src = root_dir / 'ntp'
    ntp_dst = build_outputs / 'ntp'
    if ntp_src.exists():
        atomic_copy_tree(ntp_src, ntp_dst)
        print('Copied custom NTP to build output')

    # Collect extra files (initial_preferences, policies, extensions,
    # default_extensions, ntp)
    # These are relative to build_outputs and chained into file_iter to preserve paths.
    # 'ntp' is the legacy copy kept for backwards-compat; the bundled NTP now
    # ships under Extensions/<id>/<version>/ via tools/install_ntp_extension.py.
    def extra_files_generator():
        if initial_prefs_dst.exists():
            yield Path('initial_preferences')
        for subdir in ('Extensions', 'default_extensions', 'ntp', 'policies'):
            d = build_outputs / subdir
            if d.exists():
                for f in d.rglob('*'):
                    if f.is_file():
                        yield f.relative_to(build_outputs)

    import itertools
    all_files = list(itertools.chain(files_generator, extra_files_generator()))

    # Keep the archive suffix so filescfg selects the ZIP writer while the
    # temporary sibling remains distinct from the published artifact.
    archive_stage = output.with_name(f'.{output.stem}.stage{output.suffix}')
    if archive_stage.exists():
        archive_stage.unlink()
    try:
        filescfg.create_archive(
            all_files, tuple(), build_outputs, archive_stage, timestamp)
        os.replace(archive_stage, output)
    finally:
        if archive_stage.exists():
            archive_stage.unlink()
    _create_msi(
        root_dir, build_outputs, all_files, _get_vigil_version(root_dir),
        target_cpu)
    if args.receipt:
        from devutils.release_receipt import generate_receipt

        receipt_path = root_dir / 'build' / 'release-receipt.json'
        generate_receipt(
            root_dir,
            artifact_dir=root_dir / 'build',
            output=receipt_path,
        )
        print(f'Created release receipt: {receipt_path}')

if __name__ == '__main__':
    main()
