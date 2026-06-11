"""Single source of truth: stat mode bits -> fs entry-type names.

Used by ``fileops.file_info`` and the ``dirops`` traversal filters, so the
type vocabulary (``"file"``, ``"directory"``, ``"symlink"``, ...) can never
drift between the two.
"""

from __future__ import annotations

import stat
from collections.abc import Callable

__all__ = ["ENTRY_TYPES", "type_from_mode"]

_TYPE_CHECKS: tuple[tuple[Callable[[int], bool], str], ...] = (
    (stat.S_ISLNK, "symlink"),
    (stat.S_ISDIR, "directory"),
    (stat.S_ISREG, "file"),
    (stat.S_ISFIFO, "fifo"),
    (stat.S_ISSOCK, "socket"),
    (stat.S_ISCHR, "character_device"),
    (stat.S_ISBLK, "block_device"),
)

ENTRY_TYPES: frozenset[str] = frozenset(name for _, name in _TYPE_CHECKS)
"""Every concrete entry-type name pyfs can report."""


def type_from_mode(mode: int) -> str:
    """Classify raw ``st_mode`` bits into an fs entry-type name."""
    for check, name in _TYPE_CHECKS:
        if check(mode):
            return name
    return "unknown"
