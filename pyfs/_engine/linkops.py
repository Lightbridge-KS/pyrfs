"""Link operations — the ``link_*`` family.

``link_create(path, new_path)`` creates `new_path` pointing *to* `path`
(same argument order as fs). Symbolic links are the default; pass
``symbolic=False`` for hard links.
"""

from __future__ import annotations

import os

from pyfs._engine.vectorize import PathInput, vectorized
from pyfs.errors import FsValueError
from pyfs.fspath import FsPath

__all__ = [
    "link_copy",
    "link_create",
    "link_delete",
    "link_exists",
    "link_path",
]


@vectorized
def link_create(path: str, new_path: PathInput, *, symbolic: bool = True) -> FsPath:
    """Create a link at `new_path` pointing to `path`.

    Examples
    --------
    >>> link_create("data/big.csv", "latest.csv")  # doctest: +SKIP
    FsPath('latest.csv')
    """
    dest = FsPath(new_path)
    if symbolic:
        os.symlink(path, dest)
    else:
        os.link(path, dest)
    return dest


@vectorized
def link_path(path: str) -> FsPath:
    """Return the target a symlink points to (raises if not a symlink)."""
    return FsPath(os.readlink(path))


@vectorized
def link_exists(path: str) -> bool:
    """Whether the path is a symlink (its target need not exist)."""
    return os.path.islink(path)


@vectorized
def link_copy(path: str, new_path: PathInput, *, overwrite: bool = False) -> FsPath:
    """Copy a symlink itself (the new link points to the same target).

    Raises
    ------
    FileExistsError
        If the destination exists and `overwrite` is ``False``.
    """
    target = os.readlink(path)
    dest = FsPath(new_path)
    if os.path.lexists(dest):
        if not overwrite:
            raise FileExistsError(f"target already exists: {dest!r} (pass overwrite=True)")
        os.remove(dest)
    os.symlink(target, dest)
    return dest


@vectorized
def link_delete(path: str) -> FsPath:
    """Delete a symlink (the target is untouched; non-links are refused)."""
    p = FsPath(path)
    if not os.path.islink(p):
        raise FsValueError(f"not a symlink: {p!r} (use file_delete/dir_delete)")
    os.remove(p)
    return p
