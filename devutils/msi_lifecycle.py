#!/usr/bin/env python3
"""Run a silent, recoverable MSI lifecycle check on an isolated test install.

The default mode performs administrative-image extraction only, which verifies
the MSI can be opened without modifying the host. ``--system-lifecycle`` runs
install, optional upgrade, repair, and uninstall with ``/qn`` and always tries
to remove the product in a finally block. It is intended for an elevated,
disposable Windows validation host.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _run_msiexec(arguments: list[str], log_path: Path) -> None:
    command = ["msiexec.exe", *arguments, "/qn", "/norestart", "/l*v", str(log_path)]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(command, check=False, creationflags=creationflags, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"msiexec failed with exit {result.returncode}; see {log_path}")


def extract_msi(msi_path: Path, destination: Path, log_path: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    _run_msiexec(["/a", str(msi_path), f"TARGETDIR={destination}"], log_path)
    chrome = destination / "chrome.exe"
    if not chrome.exists():
        candidates = list(destination.rglob("chrome.exe"))
        if not candidates:
            raise RuntimeError(f"administrative image has no chrome.exe under {destination}")


def _install_roots() -> list[Path]:
    roots = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Vigil",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Vigil",
    ]
    return list(dict.fromkeys(roots))


def _start_menu_roots() -> list[Path]:
    program_data = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
    return [program_data / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Vigil"]


def _assert_installed() -> None:
    if not any((root / "chrome.exe").is_file() for root in _install_roots()):
        raise RuntimeError("installed MSI has no chrome.exe under a Program Files Vigil directory")


def _assert_uninstalled() -> None:
    leftovers = [
        path for path in [*_install_roots(), *_start_menu_roots()] if path.exists()
    ]
    try:
        import winreg

        for access in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"Software\SysAdminDoc\Vigil",
                    0,
                    winreg.KEY_READ | access,
                ):
                    leftovers.append(Path(r"HKLM\Software\SysAdminDoc\Vigil"))
            except FileNotFoundError:
                pass
    except ImportError:
        pass
    if leftovers:
        raise RuntimeError(f"MSI uninstall left owned resources behind: {leftovers}")


def run_system_lifecycle(current_msi: Path, previous_msi: Path | None, work_dir: Path) -> None:
    product_code = None
    log_dir = work_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        if previous_msi:
            _run_msiexec(["/i", str(previous_msi)], log_dir / "install-previous.log")
        _run_msiexec(["/i", str(current_msi)], log_dir / "install-current.log")
        _assert_installed()
        _run_msiexec(["/fvomus", str(current_msi)], log_dir / "repair.log")
        _assert_installed()
        # /x accepts the product MSI and exercises the same major-upgrade code
        # path without requiring a registry lookup or a hard-coded product code.
        _run_msiexec(["/x", str(current_msi)], log_dir / "uninstall.log")
        _assert_uninstalled()
        product_code = "removed"
    finally:
        if product_code is None:
            # Best-effort cleanup through the current package if installation
            # reached Windows Installer but a later assertion failed.
            try:
                _run_msiexec(["/x", str(current_msi)], log_dir / "cleanup.log")
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--msi", type=Path, required=True)
    parser.add_argument("--previous-msi", type=Path)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--system-lifecycle", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    msi = args.msi.resolve()
    if not msi.is_file() or msi.suffix.lower() != ".msi":
        print(f"ERROR: MSI does not exist: {msi}", file=sys.stderr)
        return 2
    if args.previous_msi and not args.previous_msi.is_file():
        print(f"ERROR: previous MSI does not exist: {args.previous_msi}", file=sys.stderr)
        return 2

    owned_work_dir = None
    work_dir = args.work_dir.resolve() if args.work_dir else None
    try:
        if work_dir is None:
            owned_work_dir = tempfile.TemporaryDirectory(prefix="vigil-msi-")
            work_dir = Path(owned_work_dir.name)
        log_dir = work_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        if args.system_lifecycle:
            run_system_lifecycle(msi, args.previous_msi, work_dir)
            print("MSI system lifecycle passed: install, repair, uninstall")
        else:
            extract_msi(msi, work_dir / "admin-image", log_dir / "admin-image.log")
            print(f"MSI administrative-image extraction passed: {work_dir / 'admin-image'}")
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        if owned_work_dir is not None:
            owned_work_dir.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
