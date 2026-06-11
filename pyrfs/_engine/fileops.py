"""File operations — the ``file_*`` family.

Mutating verbs return the (new) path so calls chain; failures raise native
``OSError`` subclasses (``overwrite=False`` on an existing target raises
``FileExistsError``, matching fs).
"""

from __future__ import annotations

import datetime
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Iterable

from pyrfs._engine.entry_types import type_from_mode
from pyrfs._engine.vectorize import PathInput, vectorized
from pyrfs.display import parse_perms
from pyrfs.errors import FsValueError
from pyrfs.fspath import FsPath
from pyrfs.values import Bytes, Perms

__all__ = [
    "file_access",
    "file_chmod",
    "file_chown",
    "file_copy",
    "file_create",
    "file_delete",
    "file_exists",
    "file_info",
    "file_move",
    "file_show",
    "file_size",
    "file_touch",
]

_ACCESS_MODES = {
    "exists": os.F_OK,
    "read": os.R_OK,
    "write": os.W_OK,
    "execute": os.X_OK,
}

# the row schema produced by file_info/_info_one (order matters for frames)
INFO_COLUMNS = (
    "path",
    "type",
    "size",
    "permissions",
    "modification_time",
    "user",
    "group",
    "access_time",
    "change_time",
    "birth_time",
    "inode",
    "hard_links",
)


@vectorized
def file_create(path: str, *, mode: int | str = 0o644) -> FsPath:
    """Create a new file (an existing file is left unchanged).

    Vectorized: also accepts an iterable or pandas Series of paths.

    Parameters
    ----------
    path : str or os.PathLike
        The file to create. The parent directory must exist.
    mode : int or str, optional
        Permissions for a newly created file — octal string (``"644"``),
        symbolic (``"u=rw,go=r"``), or raw bits (default ``0o644``);
        subject to the process umask.

    Returns
    -------
    FsPath
        The created path (chains).

    See Also
    --------
    file_touch : Also update timestamps when the file exists.
    pyrfs.dir_create : The directory counterpart.

    Examples
    --------
    >>> file_create("notes.txt")
    FsPath('notes.txt')
    """
    p = FsPath(path)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT, parse_perms(mode))
    os.close(fd)
    return p


@vectorized
def file_copy(path: str, new_path: PathInput, *, overwrite: bool = False) -> FsPath:
    """Copy a file to `new_path` (a file name, or an existing directory).

    Vectorized: copy many files into one directory with
    ``file_copy([a, b], "dir")``.

    Parameters
    ----------
    path : str or os.PathLike
        Source file.
    new_path : str or os.PathLike
        Destination file name, or an existing directory to copy into
        (the target then becomes ``new_path/basename``).
    overwrite : bool, optional
        Allow clobbering an existing destination (default ``False``).

    Returns
    -------
    FsPath
        The path of the new copy.

    Raises
    ------
    FileExistsError
        If the (resolved) destination exists and `overwrite` is ``False``.

    See Also
    --------
    file_move : Move instead of copy.
    pyrfs.dir_copy : Copy a directory tree.
    FsPath.copy_to : Fluent equivalent.

    Examples
    --------
    >>> src = file_create("a.txt")
    >>> file_copy(src, "b.txt")
    FsPath('b.txt')
    >>> file_copy(src, "b.txt")
    Traceback (most recent call last):
        ...
    FileExistsError: target already exists: FsPath('b.txt') (pass overwrite=True)
    """
    dest = _resolve_target(path, new_path)
    if not overwrite and os.path.lexists(dest):
        raise FileExistsError(f"target already exists: {dest!r} (pass overwrite=True)")
    shutil.copy2(path, dest)
    return dest


@vectorized
def file_move(path: str, new_path: PathInput, *, overwrite: bool = False) -> FsPath:
    """Move (rename) a file — or a directory: dirs move via ``file_move``.

    Same destination resolution and ``overwrite`` guard as `file_copy`.
    There is deliberately no ``dir_move``, matching fs.

    Parameters
    ----------
    path : str or os.PathLike
        Source file or directory.
    new_path : str or os.PathLike
        Destination name, or an existing directory to move into.
    overwrite : bool, optional
        Allow clobbering an existing destination (default ``False``).

    Returns
    -------
    FsPath
        The new location.

    Raises
    ------
    FileExistsError
        If the (resolved) destination exists and `overwrite` is ``False``.

    See Also
    --------
    file_copy : Copy instead of move.
    FsPath.move_to : Fluent equivalent.

    Examples
    --------
    >>> _ = file_create("a.txt")
    >>> file_move("a.txt", "b.txt")
    FsPath('b.txt')
    """
    dest = _resolve_target(path, new_path)
    if not overwrite and os.path.lexists(dest):
        raise FileExistsError(f"target already exists: {dest!r} (pass overwrite=True)")
    if os.path.lexists(dest) and not os.path.isdir(dest):
        os.remove(dest)
    shutil.move(path, dest)
    return dest


@vectorized
def file_delete(path: str) -> FsPath:
    """Delete a file or symlink (for directories use ``dir_delete``).

    Vectorized: also accepts an iterable or pandas Series of paths.

    Returns
    -------
    FsPath
        The deleted path.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.

    See Also
    --------
    pyrfs.dir_delete : Recursive directory deletion.
    pyrfs.link_delete : Symlink-only deletion (refuses non-links).

    Examples
    --------
    >>> p = file_create("scrap.txt")
    >>> file_delete(p)
    FsPath('scrap.txt')
    >>> file_exists(p)
    False
    """
    p = FsPath(path)
    os.remove(p)
    return p


@vectorized
def file_touch(path: str) -> FsPath:
    """Update access/modification times, creating the file if needed.

    Vectorized: also accepts an iterable or pandas Series of paths.

    See Also
    --------
    file_create : Create without updating timestamps of an existing file.

    Examples
    --------
    >>> file_touch("stamp.txt")
    FsPath('stamp.txt')
    """
    p = FsPath(path)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT, 0o644)
    os.close(fd)
    os.utime(p)
    return p


@vectorized
def file_exists(path: str) -> bool:
    """Whether the path exists — a broken symlink counts as existing.

    Uses ``lexists`` (the entry itself), matching fs. Vectorized: also
    accepts an iterable or pandas Series of paths.

    See Also
    --------
    pyrfs.dir_exists : Directory-specific test (follows symlinks).
    pyrfs.is_file, pyrfs.is_dir, pyrfs.is_link : Type predicates.

    Examples
    --------
    >>> _ = file_create("here.txt")
    >>> file_exists(["here.txt", "gone.txt"])
    [True, False]
    """
    return os.path.lexists(path)


@vectorized
def file_access(path: str, mode: str = "exists") -> bool:
    """Test access to a path for the current process.

    Vectorized: also accepts an iterable or pandas Series of paths.

    Parameters
    ----------
    path : str or os.PathLike
        The path to test.
    mode : {"exists", "read", "write", "execute"}, optional
        The kind of access to check.

    Raises
    ------
    FsValueError
        If `mode` is not one of the four accepted values.

    Examples
    --------
    >>> p = file_create("data.txt")
    >>> file_access(p, "read")
    True
    """
    if mode not in _ACCESS_MODES:
        raise FsValueError(f"`mode` must be one of {sorted(_ACCESS_MODES)}, got {mode!r}")
    return os.access(path, _ACCESS_MODES[mode])


@vectorized
def file_size(path: str) -> Bytes:
    """File size as a `pyrfs.Bytes` value (compares against literals).

    Vectorized: also accepts an iterable or pandas Series of paths.

    Returns
    -------
    Bytes
        The size — an ``int`` subclass that displays humanized
        (``444.5K``) and compares against strings like ``"10KB"``.

    See Also
    --------
    pyrfs.Bytes : The typed scalar.
    file_info : Size together with the full stat row.

    Examples
    --------
    >>> p = file_create("two-bytes.bin")
    >>> with open(p, "wb") as fh:
    ...     _ = fh.write(b"hi")
    >>> file_size(p)
    Bytes(2)
    >>> file_size(p) < "1KB"
    True
    """
    return Bytes(os.stat(path).st_size)


@vectorized
def file_chmod(path: str, mode: int | str) -> FsPath:
    """Change permissions; symbolic modes apply relative to the current mode.

    Vectorized: also accepts an iterable or pandas Series of paths.

    Parameters
    ----------
    path : str or os.PathLike
        The file to change.
    mode : int or str
        Octal string (``"644"``), display form (``"rw-r--r--"``), or raw
        bits — all absolute; symbolic clauses (``"u+x"``) modify the
        *current* mode, like the ``chmod`` command.

    See Also
    --------
    pyrfs.Perms : The typed permission scalar.
    FsPath.chmod : Fluent equivalent.

    Examples
    --------
    >>> p = file_create("run.sh", mode="644")
    >>> _ = file_chmod(p, "u+x")
    >>> file_access(p, "execute")
    True
    """
    p = FsPath(path)
    current = stat.S_IMODE(os.stat(p).st_mode)
    os.chmod(p, parse_perms(mode, base=current))
    return p


@vectorized
def file_chown(path: str, user: str | int | None = None, group: str | int | None = None) -> FsPath:
    """Change owner and/or group (names or numeric ids; POSIX only).

    Parameters
    ----------
    path : str or os.PathLike
        The file to change.
    user : str or int, optional
        New owner (name or uid).
    group : str or int, optional
        New group (name or gid).

    Raises
    ------
    FsValueError
        If neither `user` nor `group` is given.
    """
    p = FsPath(path)
    if user is not None and group is not None:
        shutil.chown(p, user=user, group=group)
    elif user is not None:
        shutil.chown(p, user=user)
    elif group is not None:
        shutil.chown(p, group=group)
    else:
        raise FsValueError("at least one of `user` or `group` must be given")
    return p


@vectorized
def file_show(path: str) -> FsPath:
    """Open a file in the OS default application (``open``/``xdg-open``).

    Examples
    --------
    >>> file_show("report.pdf")  # doctest: +SKIP
    FsPath('report.pdf')
    """
    p = FsPath(path)
    if sys.platform == "darwin":
        subprocess.run(["open", p], check=False)
    elif sys.platform == "win32":
        os.startfile(p)
    else:
        subprocess.run(["xdg-open", p], check=False)
    return p


def file_info(
    path: PathInput | Iterable[PathInput], *, follow: bool = False
) -> list[dict[str, object]]:
    """Stat path(s) into rows of typed values (one dict per path).

    Row keys: ``path`` (FsPath), ``type`` (str), ``size`` (Bytes),
    ``permissions`` (Perms), ``modification_time``/``access_time``/
    ``change_time``/``birth_time`` (datetime; birth time is ``None`` where
    the OS lacks it), ``user``/``group`` (str or None), ``inode``,
    ``hard_links``.

    This is the engine form, always ``list[dict]``. The public
    `pyrfs.file_info` upgrades the result to a typed DataFrame when pandas
    is installed.

    Parameters
    ----------
    path : str, os.PathLike, or iterable of them
        Path(s) to stat.
    follow : bool, optional
        Stat the symlink target instead of the link itself
        (default ``False``, matching fs).

    Examples
    --------
    >>> p = file_create("a.txt")
    >>> row = file_info(p)[0]
    >>> row["path"], row["type"], row["size"]
    (FsPath('a.txt'), 'file', Bytes(0))
    """
    if isinstance(path, (str, os.PathLike)):
        paths: list[PathInput] = [path]
    else:
        paths = list(path)
    return [_info_one(FsPath(p), follow=follow) for p in paths]


def _resolve_target(path: str, new_path: PathInput) -> FsPath:
    """Copying/moving into an existing directory targets ``dir/basename``."""
    dest = FsPath(new_path)
    if os.path.isdir(dest):
        return dest / os.path.basename(FsPath(path))
    return dest


def _info_one(p: FsPath, *, follow: bool) -> dict[str, object]:
    st = os.stat(p) if follow else os.lstat(p)
    # macOS/BSD only; Linux/Windows stat has no birth time
    birth_time: float | None = getattr(st, "st_birthtime", None)
    return {
        "path": p,
        "type": type_from_mode(st.st_mode),
        "size": Bytes(st.st_size),
        "permissions": Perms(stat.S_IMODE(st.st_mode)),
        "modification_time": _ts(st.st_mtime),
        "user": _user_name(st.st_uid),
        "group": _group_name(st.st_gid),
        "access_time": _ts(st.st_atime),
        "change_time": _ts(st.st_ctime),
        "birth_time": _ts(birth_time) if birth_time is not None else None,
        "inode": st.st_ino,
        "hard_links": st.st_nlink,
    }


def _ts(epoch: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(epoch)


def _user_name(uid: int) -> str | None:
    try:
        import pwd

        return pwd.getpwuid(uid).pw_name
    except (ImportError, KeyError):
        return None


def _group_name(gid: int) -> str | None:
    try:
        import grp

        return grp.getgrgid(gid).gr_name
    except (ImportError, KeyError):
        return None
