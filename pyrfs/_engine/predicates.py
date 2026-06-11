"""Type predicates — the ``is_*`` family.

Like fs, ``is_file``/``is_dir`` classify by the entry itself (lstat): a
symlink answers ``True`` only to ``is_link``, even if it points to a file
or directory.
"""

from __future__ import annotations

import os

from pyrfs._engine.entry_types import type_from_mode
from pyrfs._engine.vectorize import vectorized

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
    """Whether the path is a regular file (symlinks answer ``False``).

    Classifies the entry itself (lstat), matching fs — unlike
    ``os.path.isfile``, which follows symlinks. Vectorized: also accepts an
    iterable or pandas Series of paths.

    See Also
    --------
    is_link : The predicate a symlink answers ``True`` to.
    pyrfs.file_exists : Existence regardless of type.

    Examples
    --------
    >>> from pyrfs import file_touch, link_create
    >>> _ = file_touch("data.txt")
    >>> _ = link_create("data.txt", "ln.txt")
    >>> is_file("data.txt"), is_file("ln.txt"), is_file("missing")
    (True, False, False)
    """
    return _entry_type_of(path) == "file"


@vectorized
def is_dir(path: str) -> bool:
    """Whether the path is a directory (symlinks answer ``False``).

    Classifies the entry itself (lstat), matching fs — unlike
    ``os.path.isdir`` and `pyrfs.dir_exists`, which follow symlinks.
    Vectorized: also accepts an iterable or pandas Series of paths.

    See Also
    --------
    pyrfs.dir_exists : Follow-symlink directory test.
    """
    return _entry_type_of(path) == "directory"


@vectorized
def is_link(path: str) -> bool:
    """Whether the path is a symlink (its target need not exist).

    Vectorized: also accepts an iterable or pandas Series of paths.

    See Also
    --------
    pyrfs.link_path : Read where the link points.
    """
    return _entry_type_of(path) == "symlink"


@vectorized
def is_file_empty(path: str) -> bool:
    """Whether the file exists and has size zero.

    Missing paths answer ``False`` (they are not empty files). Vectorized:
    also accepts an iterable or pandas Series of paths.
    """
    try:
        return os.stat(path).st_size == 0
    except OSError:
        return False


@vectorized
def is_dir_empty(path: str) -> bool:
    """Whether the directory exists and has no entries (hidden included).

    Missing paths answer ``False``. Vectorized: also accepts an iterable or
    pandas Series of paths.

    Examples
    --------
    >>> from pyrfs import dir_create
    >>> _ = dir_create("empty")
    >>> is_dir_empty("empty")
    True
    """
    try:
        with os.scandir(path) as it:
            return next(iter(it), None) is None
    except OSError:
        return False


@vectorized
def is_absolute_path(path: str) -> bool:
    """Whether the path is absolute (a leading ``~`` counts, as in fs).

    Pure string test — no filesystem access. Vectorized: also accepts an
    iterable or pandas Series of paths.

    Examples
    --------
    >>> is_absolute_path(["/usr", "~/data", "rel/path"])
    [True, True, False]
    """
    return path.startswith("~") or os.path.isabs(path)


def _entry_type_of(path: str) -> str | None:
    try:
        return type_from_mode(os.lstat(path).st_mode)
    except OSError:
        return None
