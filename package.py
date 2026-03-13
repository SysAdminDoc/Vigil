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
import os
import platform
import subprocess
from pathlib import Path
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parent / 'ungoogled-chromium' / 'utils'))
import filescfg
from _common import ENCODING, get_chromium_version
sys.path.pop(0)

def _get_release_revision():
    revision_path = Path(__file__).resolve().parent / 'ungoogled-chromium' / 'revision.txt'
    return revision_path.read_text(encoding=ENCODING).strip()

def _get_packaging_revision():
    revision_path = Path(__file__).resolve().parent / 'revision.txt'
    return revision_path.read_text(encoding=ENCODING).strip()

_cached_target_cpu = None

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

def main():
    """Entrypoint"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--cpu-arch',
        metavar='ARCH',
        default=platform.architecture()[0],
        choices=('64bit', '32bit'),
        help=('Filter build outputs by a target CPU. '
              'This is the same as the "arch" key in FILES.cfg. '
              'Default (from platform.architecture()): %(default)s'))
    args = parser.parse_args()

    build_outputs = Path('build/src/out/Default')

    shutil.copyfile('build/src/out/Default/mini_installer.exe',
        'build/ungoogled-chromium_{}-{}.{}_installer_{}.exe'.format(
            get_chromium_version(), _get_release_revision(),
            _get_packaging_revision(), _get_target_cpu(build_outputs)))

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
    root_dir = Path(__file__).resolve().parent
    initial_prefs_src = root_dir / 'initial_preferences'
    initial_prefs_dst = build_outputs / 'initial_preferences'
    if initial_prefs_src.exists():
        shutil.copyfile(initial_prefs_src, initial_prefs_dst)
        print('Copied initial_preferences to build output')

    # Run extension setup to download and bundle uBlock Origin
    setup_ext = root_dir / 'setup_extensions.py'
    if setup_ext.exists():
        print('Running extension setup...')
        subprocess.run([sys.executable, str(setup_ext)], cwd=str(root_dir))

    excluded_files = set([
        Path('mini_installer.exe'),
        Path('mini_installer_exe_version.rc'),
        Path('setup.exe'),
        Path('chrome.packed.7z'),
    ])
    files_generator = filescfg.filescfg_generator(
        Path('build/src/chrome/tools/build/win/FILES.cfg'),
        build_outputs, args.cpu_arch, excluded_files)

    # Copy custom NTP to build output
    ntp_src = root_dir / 'ntp'
    ntp_dst = build_outputs / 'ntp'
    if ntp_src.exists():
        if ntp_dst.exists():
            shutil.rmtree(ntp_dst)
        shutil.copytree(ntp_src, ntp_dst)
        print('Copied custom NTP to build output')

    # Collect extra files (initial_preferences, extensions, default_extensions, ntp)
    # These are relative to build_outputs and chained into file_iter to preserve paths
    def extra_files_generator():
        if initial_prefs_dst.exists():
            yield Path('initial_preferences')
        for subdir in ('Extensions', 'default_extensions', 'ntp'):
            d = build_outputs / subdir
            if d.exists():
                for f in d.rglob('*'):
                    if f.is_file():
                        yield f.relative_to(build_outputs)

    import itertools
    all_files = itertools.chain(files_generator, extra_files_generator())

    filescfg.create_archive(
        all_files, tuple(), build_outputs, output, timestamp)

if __name__ == '__main__':
    main()
