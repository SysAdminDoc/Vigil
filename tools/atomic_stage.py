"""Recoverable file and directory promotion helpers for release staging."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable


def atomic_copy_file(source: Path, target: Path) -> None:
    """Copy a file through a sibling temporary path and promote it atomically."""

    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.stage-", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_copy_tree(
    source: Path,
    target: Path,
    *,
    ignore: Callable[[str, list[str]], set[str]] | None = None,
) -> None:
    """Copy a tree and replace its target with rollback recovery.

    A stale backup is recovered when the prior process was interrupted between
    the target rename and promotion. A second backup is refused so an existing
    recovery point is never silently overwritten.
    """

    target.parent.mkdir(parents=True, exist_ok=True)
    backup = target.with_name(f".{target.name}.previous")
    if backup.exists():
        if target.exists():
            raise RuntimeError(f"refusing to overwrite stale staging backup: {backup}")
        backup.rename(target)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.stage-", dir=target.parent))
    try:
        shutil.copytree(source, temporary, dirs_exist_ok=True, ignore=ignore)
        if target.exists():
            target.rename(backup)
        try:
            temporary.rename(target)
        except Exception:
            if backup.exists() and not target.exists():
                backup.rename(target)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        if backup.exists() and not target.exists():
            backup.rename(target)
        raise
