"""Pure path algebra — the ``path_*`` family.

These functions manipulate path *strings*; none touch the filesystem except
the documented few that resolve against the running process
(``path_wd``/``path_abs``/``path_real``/``path_rel``/``path_expand``/
``path_home``/``path_temp``).
"""

from __future__ import annotations

import fnmatch
import os
import re
import tempfile
from collections.abc import Iterable
from typing import cast

from pyfs._engine.vectorize import PathInput, vectorized
from pyfs.display import tidy
from pyfs.errors import FsValueError
from pyfs.fspath import FsPath

__all__ = [
    "path",
    "path_abs",
    "path_common",
    "path_dir",
    "path_expand",
    "path_ext",
    "path_ext_remove",
    "path_ext_set",
    "path_file",
    "path_filter",
    "path_has_parent",
    "path_home",
    "path_join",
    "path_norm",
    "path_real",
    "path_rel",
    "path_sanitize",
    "path_split",
    "path_temp",
    "path_tidy",
    "path_wd",
]


def path(*parts: PathInput, ext: str = "") -> FsPath:
    """Construct a tidy path from parts, optionally adding an extension.

    Parts are joined with ``/`` (pure concatenation — an absolute later part
    does not reset the path, unlike ``os.path.join``) and tidied.

    Parameters
    ----------
    *parts : str or os.PathLike
        Path components to join.
    ext : str, optional
        Extension to append (with or without the leading dot).

    Examples
    --------
    >>> path("foo", "bar", "a", ext="txt")
    FsPath('foo/bar/a.txt')
    """
    joined = "/".join(os.fspath(p) for p in parts)
    if ext:
        joined = f"{joined}.{ext.lstrip('.')}"
    return FsPath(joined)


def path_wd() -> FsPath:
    """Return the current working directory as a tidy path."""
    return FsPath(os.getcwd())


@vectorized
def path_abs(path: str) -> FsPath:
    """Make a path absolute (against the working directory), without resolving links."""
    return FsPath(os.path.abspath(os.path.expanduser(path)))


@vectorized
def path_real(path: str) -> FsPath:
    """Canonicalize a path, resolving symlinks (touches the filesystem)."""
    return FsPath(os.path.realpath(os.path.expanduser(path)))


@vectorized
def path_norm(path: str) -> FsPath:
    """Normalize ``.`` and ``..`` components lexically (no filesystem access)."""
    return FsPath(os.path.normpath(path))


@vectorized
def path_rel(path: str, start: PathInput = ".") -> FsPath:
    """Return the path relative to `start` (default: the working directory).

    Examples
    --------
    >>> path_rel("/a/b/c", "/a")
    FsPath('b/c')
    """
    return FsPath(os.path.relpath(path, os.fspath(start)))


@vectorized
def path_expand(path: str) -> FsPath:
    """Expand a leading ``~`` to the user's home directory."""
    return FsPath(os.path.expanduser(path))


def path_home(*parts: PathInput) -> FsPath:
    """Return the user's home directory, optionally joined with `parts`."""
    return path(os.path.expanduser("~"), *parts)


def path_temp(*parts: PathInput) -> FsPath:
    """Return the session temp directory, optionally joined with `parts`."""
    return path(tempfile.gettempdir(), *parts)


@vectorized
def path_tidy(path: str) -> FsPath:
    """Tidy a path: ``/`` separators, no doubled or trailing slashes."""
    return FsPath(path)


@vectorized
def path_split(path: str) -> list[str]:
    """Split a tidy path into components (a leading root stays ``'/'``).

    Examples
    --------
    >>> path_split("/usr/bin")
    ['/', 'usr', 'bin']
    """
    t = tidy(path)
    if t == "/":
        return ["/"]
    if t.startswith("/"):
        return ["/", *t[1:].split("/")]
    return t.split("/")


def path_join(parts: Iterable[PathInput | Iterable[PathInput]]) -> FsPath | list[FsPath]:
    """Join split components back into path(s) — the inverse of :func:`path_split`."""
    items = list(parts)
    if all(isinstance(i, (str, os.PathLike)) for i in items):
        return path(*cast("list[PathInput]", items))
    return [path(*cast("Iterable[PathInput]", i)) for i in items]


@vectorized
def path_file(path: str) -> FsPath:
    """Return the file name (last component) of a path."""
    return FsPath(os.path.basename(tidy(path)))


@vectorized
def path_dir(path: str) -> FsPath:
    """Return the directory part of a path (``'.'`` if there is none)."""
    return FsPath(os.path.dirname(tidy(path)) or ".")


@vectorized
def path_ext(path: str) -> str:
    """Return the extension without the dot (``''`` if none).

    Examples
    --------
    >>> path_ext("a.tar.gz")
    'gz'
    """
    return os.path.splitext(tidy(path))[1].lstrip(".")


@vectorized
def path_ext_remove(path: str) -> FsPath:
    """Remove the extension (dotfiles like ``.gitignore`` are left intact)."""
    return FsPath(os.path.splitext(tidy(path))[0])


@vectorized
def path_ext_set(path: str, ext: str) -> FsPath:
    """Replace (or add) the extension; an empty `ext` removes it.

    Examples
    --------
    >>> path_ext_set("report.md", "html")
    FsPath('report.html')
    """
    root, _ = os.path.splitext(tidy(path))
    if not ext:
        return FsPath(root)
    return FsPath(f"{root}.{ext.lstrip('.')}")


def path_common(paths: Iterable[PathInput]) -> FsPath:
    """Return the longest common path prefix of `paths`.

    Raises
    ------
    FsValueError
        If `paths` is empty or mixes absolute and relative paths.
    """
    tidied = [tidy(p) for p in paths]
    if not tidied:
        raise FsValueError("`paths` must contain at least one path")
    try:
        return FsPath(os.path.commonpath(tidied))
    except ValueError as err:
        raise FsValueError(str(err)) from None


def path_filter(
    paths: Iterable[PathInput],
    glob: str | None = None,
    regexp: str | None = None,
    *,
    invert: bool = False,
) -> list[FsPath]:
    """Filter paths by a glob or a regular expression (mutually exclusive).

    Parameters
    ----------
    paths : iterable of str or os.PathLike
        Paths to filter.
    glob : str, optional
        Wildcard pattern matched against the whole path (e.g. ``"*.py"``).
    regexp : str, optional
        Regular expression searched within the path.
    invert : bool, optional
        Keep the paths that do *not* match.

    Raises
    ------
    FsValueError
        If both `glob` and `regexp` are set.
    """
    if glob is not None and regexp is not None:
        raise FsValueError("`glob` and `regexp` cannot both be set.")
    tidied = [FsPath(p) for p in paths]
    pattern = fnmatch.translate(glob) if glob is not None else regexp
    if pattern is None:
        return tidied
    rx = re.compile(pattern)
    return [p for p in tidied if (rx.search(p) is not None) != invert]


@vectorized
def path_has_parent(path: str, parent: PathInput) -> bool:
    """Return whether `path` sits at or below `parent`.

    Both are anchored to the working directory before comparing, so relative
    and absolute forms compare consistently.
    """
    child_parts = _abs_parts(path)
    parent_parts = _abs_parts(os.fspath(parent))
    return child_parts[: len(parent_parts)] == parent_parts


_SANITIZE_CONTROL = re.compile(r"[\x00-\x1f\x80-\x9f]")
_SANITIZE_ILLEGAL = re.compile(r'[/\\?<>:*|"]')
_SANITIZE_WIN_TRAILING = re.compile(r"[. ]+$")
_SANITIZE_RESERVED = re.compile(r"^\.+$")
_SANITIZE_WIN_RESERVED = re.compile(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", re.IGNORECASE)


@vectorized
def path_sanitize(filename: str, replacement: str = "") -> str:
    """Turn an untrusted string into a filename safe on all major OSes.

    Removes control characters, characters illegal in filenames, trailing
    dots/spaces, and Windows-reserved device names; truncates to 255 chars.
    """
    out = _SANITIZE_CONTROL.sub(replacement, filename)
    out = _SANITIZE_ILLEGAL.sub(replacement, out)
    out = _SANITIZE_WIN_TRAILING.sub(replacement, out)
    if _SANITIZE_RESERVED.match(out) or _SANITIZE_WIN_RESERVED.match(out):
        out = replacement
    return out[:255]


def _abs_parts(p: str) -> list[str]:
    t = tidy(os.path.abspath(os.path.expanduser(p)))
    if t == "/":
        return [""]
    return t.split("/")
