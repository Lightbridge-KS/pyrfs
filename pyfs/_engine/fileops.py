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

from pyfs._engine.vectorize import PathInput, vectorized
from pyfs.display import parse_perms
from pyfs.errors import FsValueError
from pyfs.fspath import FsPath
from pyfs.values import Bytes, Perms

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


@vectorized
def file_create(path: str, *, mode: int | str = 0o644) -> FsPath:
    """Create a new file (left unchanged if it already exists).

    Examples
    --------
    >>> file_create("notes.txt")  # doctest: +SKIP
    FsPath('notes.txt')
    """
    p = FsPath(path)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT, parse_perms(mode))
    os.close(fd)
    return p


@vectorized
def file_copy(path: str, new_path: PathInput, *, overwrite: bool = False) -> FsPath:
    """Copy a file to `new_path` (a file name, or an existing directory).

    Parameters
    ----------
    path : str or os.PathLike
        Source file.
    new_path : str or os.PathLike
        Destination file, or an existing directory to copy into.
    overwrite : bool, optional
        Allow clobbering an existing destination file (default ``False``).

    Returns
    -------
    FsPath
        The path of the new copy.

    Raises
    ------
    FileExistsError
        If the destination exists and `overwrite` is ``False``.
    """
    dest = _resolve_target(path, new_path)
    if not overwrite and os.path.lexists(dest):
        raise FileExistsError(f"target already exists: {dest!r} (pass overwrite=True)")
    shutil.copy2(path, dest)
    return dest


@vectorized
def file_move(path: str, new_path: PathInput, *, overwrite: bool = False) -> FsPath:
    """Move (rename) a file — or a directory; dirs move via ``file_move``.

    Same destination resolution and ``overwrite`` guard as :func:`file_copy`.
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
    """Delete a file or symlink (directories: use ``dir_delete``)."""
    p = FsPath(path)
    os.remove(p)
    return p


@vectorized
def file_touch(path: str) -> FsPath:
    """Update access/modification times, creating the file if needed."""
    p = FsPath(path)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT, 0o644)
    os.close(fd)
    os.utime(p)
    return p


@vectorized
def file_exists(path: str) -> bool:
    """Whether the path exists (a broken symlink counts as existing)."""
    return os.path.lexists(path)


_ACCESS_MODES = {
    "exists": os.F_OK,
    "read": os.R_OK,
    "write": os.W_OK,
    "execute": os.X_OK,
}


@vectorized
def file_access(path: str, mode: str = "exists") -> bool:
    """Test access: ``"exists"``, ``"read"``, ``"write"``, or ``"execute"``."""
    if mode not in _ACCESS_MODES:
        raise FsValueError(f"`mode` must be one of {sorted(_ACCESS_MODES)}, got {mode!r}")
    return os.access(path, _ACCESS_MODES[mode])


@vectorized
def file_size(path: str) -> Bytes:
    """File size as a :class:`~pyfs.Bytes` value.

    Examples
    --------
    >>> file_size("data.csv") > "10KB"  # doctest: +SKIP
    True
    """
    return Bytes(os.stat(path).st_size)


@vectorized
def file_chmod(path: str, mode: int | str) -> FsPath:
    """Change permissions; symbolic modes apply relative to the current mode.

    Examples
    --------
    >>> file_chmod("run.sh", "u+x")  # doctest: +SKIP
    FsPath('run.sh')
    """
    p = FsPath(path)
    current = stat.S_IMODE(os.stat(p).st_mode)
    os.chmod(p, parse_perms(mode, base=current))
    return p


@vectorized
def file_chown(path: str, user: str | int | None = None, group: str | int | None = None) -> FsPath:
    """Change owner and/or group (names or numeric ids; POSIX only)."""
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
    """Open a file in the OS default application (cross-platform)."""
    p = FsPath(path)
    if sys.platform == "darwin":
        subprocess.run(["open", p], check=False)
    elif sys.platform == "win32":
        os.startfile(p)
    else:
        subprocess.run(["xdg-open", p], check=False)
    return p


_FILE_TYPES = [
    (stat.S_ISLNK, "symlink"),
    (stat.S_ISDIR, "directory"),
    (stat.S_ISREG, "file"),
    (stat.S_ISFIFO, "fifo"),
    (stat.S_ISSOCK, "socket"),
    (stat.S_ISCHR, "character_device"),
    (stat.S_ISBLK, "block_device"),
]


def file_info(
    path: PathInput | Iterable[PathInput], *, follow: bool = False
) -> list[dict[str, object]]:
    """Stat path(s) into rows of typed values (one dict per path).

    Columns: ``path`` (FsPath), ``type`` (str), ``size`` (Bytes),
    ``permissions`` (Perms), ``modification_time``/``access_time``/
    ``change_time``/``birth_time`` (datetime or None), ``user``/``group``
    (str or None), ``inode``, ``hard_links``.

    With pandas installed the public surface upgrades this to a DataFrame
    (P5); the engine always returns ``list[dict]``.
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
    return {
        "path": p,
        "type": _file_type(st.st_mode),
        "size": Bytes(st.st_size),
        "permissions": Perms(stat.S_IMODE(st.st_mode)),
        "modification_time": _ts(st.st_mtime),
        "user": _user_name(st.st_uid),
        "group": _group_name(st.st_gid),
        "access_time": _ts(st.st_atime),
        "change_time": _ts(st.st_ctime),
        "birth_time": _ts(st.st_birthtime) if hasattr(st, "st_birthtime") else None,
        "inode": st.st_ino,
        "hard_links": st.st_nlink,
    }


def _file_type(mode: int) -> str:
    for check, name in _FILE_TYPES:
        if check(mode):
            return name
    return "unknown"


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
