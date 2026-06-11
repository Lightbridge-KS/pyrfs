"""Directory operations — the ``dir_*`` family.

``dir_walk`` is the lazy core traversal (a generator — the Pythonic take on
fs's callback walker); ``dir_ls`` and ``dir_map`` are built on it. All
traversals share the fs filter set: ``all``, ``recurse`` (bool or depth),
``type``, ``glob``/``regexp`` (mutually exclusive), ``invert``, ``fail``.
"""

from __future__ import annotations

import fnmatch
import os
import re
import shutil
import warnings
from collections.abc import Callable, Iterable, Iterator

from pyrfs._engine.entry_types import ENTRY_TYPES, type_from_mode
from pyrfs._engine.fileops import file_info
from pyrfs._engine.vectorize import PathInput, vectorized
from pyrfs.display import colourise_path, parse_perms
from pyrfs.errors import FsValueError
from pyrfs.fspath import FsPath

__all__ = [
    "dir_copy",
    "dir_create",
    "dir_delete",
    "dir_exists",
    "dir_info",
    "dir_ls",
    "dir_map",
    "dir_tree",
    "dir_walk",
]


@vectorized
def dir_create(path: str, *, mode: int | str = 0o755, recurse: bool = True) -> FsPath:
    """Create a directory (parents too when `recurse`); existing dirs are fine.

    Vectorized: also accepts an iterable or pandas Series of paths.

    Parameters
    ----------
    path : str or os.PathLike
        The directory to create.
    mode : int or str, optional
        Permissions for newly created directories (default ``0o755``);
        subject to the process umask.
    recurse : bool, optional
        Create missing parents too (default ``True``, matching fs — note
        this differs from the ``recurse=False`` default of the listing
        functions).

    Returns
    -------
    FsPath
        The created path (chains).

    See Also
    --------
    file_create : The file counterpart.
    FsPath.mkdir : Fluent equivalent.

    Examples
    --------
    >>> dir_create("out/plots")
    FsPath('out/plots')
    >>> dir_exists("out/plots")
    True
    """
    p = FsPath(path)
    m = parse_perms(mode)
    if recurse:
        os.makedirs(p, mode=m, exist_ok=True)
    elif not os.path.isdir(p):
        os.mkdir(p, mode=m)
    return p


@vectorized
def dir_exists(path: str) -> bool:
    """Whether the path exists and is a directory (follows symlinks).

    Vectorized: also accepts an iterable or pandas Series of paths.

    See Also
    --------
    pyrfs.is_dir : Entry-itself (lstat) semantics — a symlink to a
        directory answers ``False`` there but ``True`` here.
    """
    return os.path.isdir(path)


@vectorized
def dir_delete(path: str) -> FsPath:
    """Delete a directory and everything below it (recursive, like ``rm -rf``).

    Vectorized: also accepts an iterable or pandas Series of paths.

    Returns
    -------
    FsPath
        The deleted path.

    See Also
    --------
    file_delete : Single files and symlinks.
    FsPath.rmdir : Fluent equivalent.

    Examples
    --------
    >>> _ = dir_create("scratch/deep")
    >>> dir_delete("scratch")
    FsPath('scratch')
    >>> dir_exists("scratch")
    False
    """
    p = FsPath(path)
    shutil.rmtree(p)
    return p


@vectorized
def dir_copy(path: str, new_path: PathInput, *, overwrite: bool = False) -> FsPath:
    """Copy a directory tree to `new_path` (a name, or an existing directory).

    Same destination resolution and ``overwrite`` guard as `file_copy`:
    copying into an existing directory targets ``new_path/basename`` (shell
    ``cp -r`` semantics). With ``overwrite=True`` an existing destination is
    *replaced*, not merged. Symlinks are copied as symlinks.

    Parameters
    ----------
    path : str or os.PathLike
        Source directory.
    new_path : str or os.PathLike
        Destination name, or an existing directory to copy into.
    overwrite : bool, optional
        Replace an existing (resolved) destination (default ``False``).

    Returns
    -------
    FsPath
        The root of the new copy.

    Raises
    ------
    NotADirectoryError
        If `path` is not a directory.
    FileExistsError
        If the (resolved) destination exists and `overwrite` is ``False``.

    See Also
    --------
    file_copy : Single files.
    file_move : Directories move via ``file_move`` (there is no dir_move).

    Examples
    --------
    >>> _ = dir_create("src/sub")
    >>> dir_copy("src", "backup")
    FsPath('backup')
    >>> dir_exists("backup/sub")
    True
    """
    src = FsPath(path)
    if not os.path.isdir(src):
        raise NotADirectoryError(f"not a directory: {src!r}")
    dest = FsPath(new_path)
    if os.path.isdir(dest):
        dest = dest / os.path.basename(src)
    if os.path.lexists(dest):
        if not overwrite:
            raise FileExistsError(f"target already exists: {dest!r} (pass overwrite=True)")
        if os.path.isdir(dest) and not os.path.islink(dest):
            shutil.rmtree(dest)
        else:
            os.remove(dest)
    shutil.copytree(src, dest, symlinks=True)
    return dest


def dir_walk(
    path: PathInput = ".",
    *,
    all: bool = False,
    recurse: bool | int = False,
    type: str | Iterable[str] = "any",
    glob: str | None = None,
    regexp: str | None = None,
    invert: bool = False,
    fail: bool = True,
) -> Iterator[FsPath]:
    """Lazily yield directory entries, with the full fs filter set.

    Parameters
    ----------
    path : str or os.PathLike
        Directory to walk.
    all : bool, optional
        Include hidden dotfiles.
    recurse : bool or int, optional
        ``True`` = full recursion, ``False`` = this level only, an int
        limits depth (``1`` = one level below `path`).
    type : str or iterable of str, optional
        Keep only these entry types (``"file"``, ``"directory"``,
        ``"symlink"``, ...); ``"any"`` keeps all.
    glob, regexp : str, optional
        Keep entries whose path matches (mutually exclusive).
    invert : bool, optional
        Keep entries that do *not* match `glob`/`regexp`.
    fail : bool, optional
        Raise on unreadable entries (``True``) or warn and skip (``False``).

    Yields
    ------
    FsPath
        Entry paths, prefixed by `path`, siblings sorted by name.

    Raises
    ------
    FsValueError
        If both `glob` and `regexp` are set, or `type` names an unknown
        entry type.

    See Also
    --------
    dir_ls : The eager (list-returning) form.
    dir_map : Apply a function to each entry.

    Examples
    --------
    >>> from pyrfs import file_touch
    >>> _ = dir_create("logs")
    >>> _ = file_touch("logs/a.log")
    >>> walker = dir_walk("logs")  # nothing read yet — it's a generator
    >>> next(walker)
    FsPath('logs/a.log')
    """
    if glob is not None and regexp is not None:
        raise FsValueError("`glob` and `regexp` cannot both be set.")
    wanted = _normalize_types(type)
    pattern = (
        re.compile(fnmatch.translate(glob))
        if glob is not None
        else (re.compile(regexp) if regexp is not None else None)
    )
    depth = _depth_budget(recurse)
    for entry_path, entry_type in _scan(FsPath(path), depth, all=all, fail=fail):
        if wanted is not None and entry_type not in wanted:
            continue
        if pattern is not None and (pattern.search(entry_path) is not None) == invert:
            continue
        yield entry_path


def dir_ls(
    path: PathInput = ".",
    *,
    all: bool = False,
    recurse: bool | int = False,
    type: str | Iterable[str] = "any",
    glob: str | None = None,
    regexp: str | None = None,
    invert: bool = False,
    fail: bool = True,
) -> list[FsPath]:
    """List directory entries with the full fs filter set.

    The eager form of `dir_walk` — same parameters, returns a sorted list.

    Parameters
    ----------
    path : str or os.PathLike
        Directory to list (default: the working directory).
    all : bool, optional
        Include hidden dotfiles.
    recurse : bool or int, optional
        ``True`` = full recursion, ``False`` = this level only, an int
        limits depth (``1`` = one level below `path`).
    type : str or iterable of str, optional
        Keep only these entry types (``"file"``, ``"directory"``,
        ``"symlink"``, ...); ``"any"`` keeps all.
    glob, regexp : str, optional
        Keep entries whose path matches (mutually exclusive).
    invert : bool, optional
        Keep entries that do *not* match `glob`/`regexp`.
    fail : bool, optional
        Raise on unreadable entries (``True``) or warn and skip (``False``).

    Returns
    -------
    list of FsPath
        Entry paths, prefixed by `path`, siblings sorted by name.

    Raises
    ------
    FsValueError
        If both `glob` and `regexp` are set, or `type` names an unknown
        entry type.

    See Also
    --------
    dir_walk : The lazy (generator) form.
    dir_info : The same listing as typed stat rows / DataFrame.
    pyrfs.path_filter : The same glob/regexp filter for in-memory lists.

    Examples
    --------
    >>> from pyrfs import file_touch
    >>> _ = dir_create("proj/sub")
    >>> _ = file_touch(["proj/a.py", "proj/b.txt"])
    >>> dir_ls("proj")
    [FsPath('proj/a.py'), FsPath('proj/b.txt'), FsPath('proj/sub')]
    >>> dir_ls("proj", glob="*.py")
    [FsPath('proj/a.py')]
    >>> dir_ls("proj", type="directory")
    [FsPath('proj/sub')]
    """
    return list(
        dir_walk(
            path,
            all=all,
            recurse=recurse,
            type=type,
            glob=glob,
            regexp=regexp,
            invert=invert,
            fail=fail,
        )
    )


def dir_map(
    path: PathInput,
    fn: Callable[[FsPath], object],
    *,
    all: bool = False,
    recurse: bool | int = False,
    type: str | Iterable[str] = "any",
    glob: str | None = None,
    regexp: str | None = None,
    invert: bool = False,
    fail: bool = True,
) -> list[object]:
    """Apply `fn` to each entry and collect the results.

    Takes the same filter arguments as `dir_ls`.

    See Also
    --------
    dir_walk : Iterate lazily instead of collecting.

    Examples
    --------
    >>> from pyrfs import file_touch
    >>> _ = dir_create("d")
    >>> _ = file_touch(["d/a.py", "d/b.py"])
    >>> dir_map("d", lambda p: p.ext())
    ['py', 'py']
    """
    return [
        fn(p)
        for p in dir_walk(
            path,
            all=all,
            recurse=recurse,
            type=type,
            glob=glob,
            regexp=regexp,
            invert=invert,
            fail=fail,
        )
    ]


def dir_info(
    path: PathInput = ".",
    *,
    all: bool = False,
    recurse: bool | int = False,
    type: str | Iterable[str] = "any",
    glob: str | None = None,
    regexp: str | None = None,
    invert: bool = False,
    fail: bool = True,
) -> list[dict[str, object]]:
    """Stat each entry into typed rows — `file_info` over `dir_ls`.

    Takes the same filter arguments as `dir_ls`. This is the engine form,
    always ``list[dict]``; the public `pyrfs.dir_info` upgrades the result
    to a typed DataFrame when pandas is installed.

    See Also
    --------
    pyrfs.dir_info : The public, DataFrame-returning surface.
    file_info : The row schema.
    """
    return file_info(
        dir_ls(
            path,
            all=all,
            recurse=recurse,
            type=type,
            glob=glob,
            regexp=regexp,
            invert=invert,
            fail=fail,
        )
    )


def dir_tree(
    path: PathInput = ".",
    *,
    recurse: bool | int = True,
    all: bool = False,
) -> None:
    """Print a box-drawing tree of the directory, like the Unix ``tree``.

    Entries are coloured by type via ``LS_COLORS`` in a capable terminal
    (plain on non-TTY or ``NO_COLOR``). Hidden files are skipped unless
    ``all=True``; `recurse` limits depth as in `dir_ls`.

    Examples
    --------
    >>> from pyrfs import file_touch
    >>> _ = dir_create("proj/src")
    >>> _ = file_touch("proj/README.md")
    >>> dir_tree("proj")
    proj
    ├── README.md
    └── src
    """
    root = FsPath(path)
    lines = [colourise_path(root)]
    _tree_lines(root, "", _depth_budget(recurse), all, lines)
    print("\n".join(lines))


def _normalize_types(type: str | Iterable[str]) -> set[str] | None:
    wanted = {type} if isinstance(type, str) else set(type)
    unknown = wanted - ENTRY_TYPES - {"any"}
    if unknown:
        raise FsValueError(f"unknown `type` value(s): {sorted(unknown)}")
    if "any" in wanted:
        return None
    return wanted


def _depth_budget(recurse: bool | int) -> int:
    """Levels to descend below the top: -1 = unlimited, 0 = none."""
    if recurse is True:
        return -1
    if recurse is False:
        return 0
    return int(recurse)


def _scan(path: FsPath, depth: int, *, all: bool, fail: bool) -> Iterator[tuple[FsPath, str]]:
    """Yield (path, type) under `path`, depth-limited, sorted by name."""
    try:
        entries = sorted(os.scandir(path), key=lambda e: e.name)
    except OSError as err:
        if fail:
            raise
        warnings.warn(f"skipping unreadable directory: {err}", stacklevel=2)
        return
    for entry in entries:
        if not all and entry.name.startswith("."):
            continue
        entry_path = path / entry.name
        entry_type = _entry_type(entry, fail=fail)
        if entry_type is None:
            continue
        yield entry_path, entry_type
        if entry_type == "directory" and depth != 0:
            yield from _scan(entry_path, depth - 1, all=all, fail=fail)


def _entry_type(entry: os.DirEntry[str], *, fail: bool) -> str | None:
    try:
        mode = entry.stat(follow_symlinks=False).st_mode
    except OSError as err:
        if fail:
            raise
        warnings.warn(f"skipping unreadable entry: {err}", stacklevel=2)
        return None
    return type_from_mode(mode)


def _tree_lines(path: FsPath, prefix: str, depth: int, all: bool, lines: list[str]) -> None:
    try:
        entries = sorted(os.scandir(path), key=lambda e: e.name)
    except OSError:
        return
    visible = [e for e in entries if all or not e.name.startswith(".")]
    for i, entry in enumerate(visible):
        last = i == len(visible) - 1
        label = colourise_path(path / entry.name, entry.name)
        lines.append(f"{prefix}{'└── ' if last else '├── '}{label}")
        if entry.is_dir(follow_symlinks=False) and depth != 0:
            _tree_lines(
                path / entry.name,
                f"{prefix}{'    ' if last else '│   '}",
                depth - 1,
                all,
                lines,
            )
