"""Link operations — the ``link_*`` family.

``link_create(path, new_path)`` creates `new_path` pointing *to* `path`
(same argument order as fs). Symbolic links are the default; pass
``symbolic=False`` for hard links.
"""

from __future__ import annotations

import os

from pyrfs._engine.vectorize import PathInput, vectorized
from pyrfs.errors import FsValueError
from pyrfs.fspath import FsPath

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

    Note the argument order (fs's): target first, link name second.

    Parameters
    ----------
    path : str or os.PathLike
        What the link points to (need not exist for symbolic links).
    new_path : str or os.PathLike
        Where to create the link.
    symbolic : bool, optional
        Symbolic link (default) or hard link.

    Returns
    -------
    FsPath
        The new link's path.

    Raises
    ------
    FileExistsError
        If `new_path` already exists.

    See Also
    --------
    link_path : Read where a symlink points.

    Examples
    --------
    >>> from pyrfs import file_touch
    >>> _ = file_touch("big.csv")
    >>> link_create("big.csv", "latest.csv")
    FsPath('latest.csv')
    >>> link_path("latest.csv")
    FsPath('big.csv')
    """
    dest = FsPath(new_path)
    if symbolic:
        os.symlink(path, dest)
    else:
        os.link(path, dest)
    return dest


@vectorized
def link_path(path: str) -> FsPath:
    """Return the target a symlink points to (``OSError`` if not a symlink).

    Vectorized: also accepts an iterable or pandas Series of paths.

    See Also
    --------
    pyrfs.path_real : Fully resolve a path through all links.
    """
    return FsPath(os.readlink(path))


@vectorized
def link_exists(path: str) -> bool:
    """Whether the path is a symlink (its target need not exist).

    Equivalent to `pyrfs.is_link`. Vectorized: also accepts an iterable or
    pandas Series of paths.
    """
    return os.path.islink(path)


@vectorized
def link_copy(path: str, new_path: PathInput, *, overwrite: bool = False) -> FsPath:
    """Copy a symlink itself (the new link points to the same target).

    The target is *not* copied — use `pyrfs.file_copy` to copy what the
    link points to.

    Parameters
    ----------
    path : str or os.PathLike
        An existing symlink.
    new_path : str or os.PathLike
        Where to create the duplicate link.
    overwrite : bool, optional
        Allow clobbering an existing destination (default ``False``).

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
    """Delete a symlink — the target is untouched; non-links are refused.

    Raises
    ------
    FsValueError
        If `path` is not a symlink (use `pyrfs.file_delete` or
        `pyrfs.dir_delete` for real files).

    Examples
    --------
    >>> from pyrfs import file_exists, file_touch
    >>> _ = file_touch("real.txt")
    >>> _ = link_create("real.txt", "ln.txt")
    >>> _ = link_delete("ln.txt")
    >>> file_exists("real.txt")  # target survives
    True
    """
    p = FsPath(path)
    if not os.path.islink(p):
        raise FsValueError(f"not a symlink: {p!r} (use file_delete/dir_delete)")
    os.remove(p)
    return p
