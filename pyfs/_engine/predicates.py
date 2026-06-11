"""Type predicates — the ``is_*`` family.

Like fs, ``is_file``/``is_dir`` classify by the entry itself (lstat): a
symlink answers ``True`` only to ``is_link``, even if it points to a file
or directory.
"""

from __future__ import annotations

import os

from pyfs._engine.entry_types import type_from_mode
from pyfs._engine.vectorize import vectorized

__all__ = [
    "is_absolute_path",
    "is_dir",
    "is_dir_empty",
    "is_file",
    "is_file_empty",
    "is_link",
]


@vectorized
def is_file(path: str) -> bool:
    """Whether the path is a regular file (symlinks answer ``False``)."""
    return _entry_type_of(path) == "file"


@vectorized
def is_dir(path: str) -> bool:
    """Whether the path is a directory (symlinks answer ``False``)."""
    return _entry_type_of(path) == "directory"


@vectorized
def is_link(path: str) -> bool:
    """Whether the path is a symlink (its target need not exist)."""
    return _entry_type_of(path) == "symlink"


@vectorized
def is_file_empty(path: str) -> bool:
    """Whether the file exists and has size zero."""
    try:
        return os.stat(path).st_size == 0
    except OSError:
        return False


@vectorized
def is_dir_empty(path: str) -> bool:
    """Whether the directory exists and has no entries (hidden included)."""
    try:
        with os.scandir(path) as it:
            return next(iter(it), None) is None
    except OSError:
        return False


@vectorized
def is_absolute_path(path: str) -> bool:
    """Whether the path is absolute (a leading ``~`` counts, as in fs)."""
    return path.startswith("~") or os.path.isabs(path)


def _entry_type_of(path: str) -> str | None:
    try:
        return type_from_mode(os.lstat(path).st_mode)
    except OSError:
        return None
