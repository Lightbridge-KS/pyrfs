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

from pyfs._engine.entry_types import ENTRY_TYPES, type_from_mode
from pyfs._engine.fileops import file_info
from pyfs._engine.vectorize import PathInput, vectorized
from pyfs.display import parse_perms
from pyfs.errors import FsValueError
from pyfs.fspath import FsPath

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

    Examples
    --------
    >>> dir_create("out/plots")  # doctest: +SKIP
    FsPath('out/plots')
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
    """Whether the path exists and is a directory (follows symlinks)."""
    return os.path.isdir(path)


@vectorized
def dir_delete(path: str) -> FsPath:
    """Delete a directory and everything below it (recursive)."""
    p = FsPath(path)
    shutil.rmtree(p)
    return p


@vectorized
def dir_copy(path: str, new_path: PathInput, *, overwrite: bool = False) -> FsPath:
    """Copy a directory tree to `new_path` (a name, or an existing directory).

    Same destination resolution and ``overwrite`` guard as ``file_copy``;
    with ``overwrite=True`` an existing destination is replaced, not merged.
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
    """List directory entries (eager :func:`dir_walk`; same filters).

    Examples
    --------
    >>> dir_ls("pyfs", recurse=True, glob="*.py")  # doctest: +SKIP
    [FsPath('pyfs/__init__.py'), ...]
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
    """Apply `fn` to each entry (same filters as :func:`dir_walk`)."""
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
    """Stat each entry into typed rows — ``file_info`` over ``dir_ls``."""
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

    Examples
    --------
    >>> dir_tree("pyfs")  # doctest: +SKIP
    pyfs
    ├── __init__.py
    └── _engine
        └── paths.py
    """
    root = FsPath(path)
    lines = [str(root)]
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
        lines.append(f"{prefix}{'└── ' if last else '├── '}{entry.name}")
        if entry.is_dir(follow_symlinks=False) and depth != 0:
            _tree_lines(
                path / entry.name,
                f"{prefix}{'    ' if last else '│   '}",
                depth - 1,
                all,
                lines,
            )
