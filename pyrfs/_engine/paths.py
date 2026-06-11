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

from pyrfs._engine.vectorize import PathInput, vectorized
from pyrfs.display import tidy
from pyrfs.errors import FsValueError
from pyrfs.fspath import FsPath

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

# path_sanitize: characters/names unsafe in filenames across OSes
_SANITIZE_CONTROL = re.compile(r"[\x00-\x1f\x80-\x9f]")
_SANITIZE_ILLEGAL = re.compile(r'[/\\?<>:*|"]')
_SANITIZE_WIN_TRAILING = re.compile(r"[. ]+$")
_SANITIZE_RESERVED = re.compile(r"^\.+$")
_SANITIZE_WIN_RESERVED = re.compile(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", re.IGNORECASE)


def path(*parts: PathInput, ext: str = "") -> FsPath:
    """Construct a tidy path from parts, optionally adding an extension.

    Parts are joined with ``/`` and tidied. The join is pure concatenation —
    an absolute later part does *not* reset the path, unlike
    ``os.path.join``.

    Parameters
    ----------
    *parts : str or os.PathLike
        Path components to join.
    ext : str, optional
        Extension to append, with or without the leading dot (one dot is
        guaranteed, never doubled).

    Returns
    -------
    FsPath
        The joined, tidy path.

    See Also
    --------
    path_join : Join components given as a list (inverse of `path_split`).
    FsPath.__truediv__ : The fluent ``/`` join operator.

    Examples
    --------
    >>> path("foo", "bar", "a", ext="txt")
    FsPath('foo/bar/a.txt')
    >>> path("a/", "/b")  # concatenation, not os.path.join reset
    FsPath('a/b')
    """
    joined = "/".join(os.fspath(p) for p in parts)
    if ext:
        joined = f"{joined}.{ext.lstrip('.')}"
    return FsPath(joined)


def path_wd() -> FsPath:
    """Return the current working directory as a tidy path.

    See Also
    --------
    path_abs : Anchor a relative path to the working directory.
    """
    return FsPath(os.getcwd())


@vectorized
def path_abs(path: str) -> FsPath:
    """Make a path absolute against the working directory (links unresolved).

    A leading ``~`` is expanded first. Vectorized: also accepts an iterable
    or pandas Series of paths.

    See Also
    --------
    path_real : Also resolve symlinks (canonical form).
    path_norm : Lexical ``.``/``..`` normalization only.

    Examples
    --------
    >>> path_abs("data").startswith("/")
    True
    """
    return FsPath(os.path.abspath(os.path.expanduser(path)))


@vectorized
def path_real(path: str) -> FsPath:
    """Canonicalize a path, resolving symlinks (touches the filesystem).

    Vectorized: also accepts an iterable or pandas Series of paths.

    See Also
    --------
    path_abs : Absolute form without resolving links.
    """
    return FsPath(os.path.realpath(os.path.expanduser(path)))


@vectorized
def path_norm(path: str) -> FsPath:
    """Normalize ``.`` and ``..`` components lexically (no filesystem access).

    Vectorized: also accepts an iterable or pandas Series of paths.

    Examples
    --------
    >>> path_norm("a/../b/./c")
    FsPath('b/c')
    """
    return FsPath(os.path.normpath(path))


@vectorized
def path_rel(path: str, start: PathInput = ".") -> FsPath:
    """Return the path expressed relative to `start`.

    Vectorized: also accepts an iterable or pandas Series of paths.

    Parameters
    ----------
    path : str or os.PathLike
        The path to re-express.
    start : str or os.PathLike, optional
        The anchor directory (default: the working directory).

    See Also
    --------
    path_has_parent : Test containment instead of computing the relation.
    FsPath.rel_to : Fluent equivalent.

    Examples
    --------
    >>> path_rel("/a/b/c", "/a")
    FsPath('b/c')
    >>> path_rel("/a/b", "/a/d")
    FsPath('../b')
    """
    return FsPath(os.path.relpath(path, os.fspath(start)))


@vectorized
def path_expand(path: str) -> FsPath:
    """Expand a leading ``~`` to the user's home directory.

    Vectorized: also accepts an iterable or pandas Series of paths.

    See Also
    --------
    path_home : Build paths under the home directory directly.
    """
    return FsPath(os.path.expanduser(path))


def path_home(*parts: PathInput) -> FsPath:
    """Return the user's home directory, optionally joined with `parts`.

    Examples
    --------
    >>> path_home("data").endswith("/data")
    True
    """
    return path(os.path.expanduser("~"), *parts)


def path_temp(*parts: PathInput) -> FsPath:
    """Return the session temp directory, optionally joined with `parts`.

    See Also
    --------
    pyrfs.file_temp : A unique temp *file name* (not just the directory).
    """
    return path(tempfile.gettempdir(), *parts)


@vectorized
def path_tidy(path: str) -> FsPath:
    """Tidy a path: ``/`` separators, no doubled or trailing slashes.

    Every pyrfs function already returns tidy paths; use this to normalize
    paths from elsewhere. Vectorized: also accepts an iterable or pandas
    Series of paths.

    Examples
    --------
    >>> path_tidy("src//a.txt/")
    FsPath('src/a.txt')
    >>> path_tidy("C:\\\\data\\\\x")
    FsPath('C:/data/x')
    """
    return FsPath(path)


@vectorized
def path_split(path: str) -> list[str]:
    """Split a tidy path into components (a leading root stays ``'/'``).

    Vectorized: a list of paths yields a list of component lists.

    See Also
    --------
    path_join : The inverse operation.
    FsPath.parts : Fluent equivalent.

    Examples
    --------
    >>> path_split("/usr/bin")
    ['/', 'usr', 'bin']
    >>> path_split("a/b")
    ['a', 'b']
    """
    t = tidy(path)
    if t == "/":
        return ["/"]
    if t.startswith("/"):
        return ["/", *t[1:].split("/")]
    return t.split("/")


def path_join(parts: Iterable[PathInput | Iterable[PathInput]]) -> FsPath | list[FsPath]:
    """Join split components back into path(s) — the inverse of `path_split`.

    Parameters
    ----------
    parts : iterable
        Either one sequence of components, or a sequence of such sequences
        (joining each one).

    See Also
    --------
    path : Variadic construction with an optional extension.

    Examples
    --------
    >>> path_join(["/", "usr", "bin"])
    FsPath('/usr/bin')
    >>> path_join([["a", "b"], ["c", "d"]])
    [FsPath('a/b'), FsPath('c/d')]
    """
    items = list(parts)
    if all(isinstance(i, (str, os.PathLike)) for i in items):
        return path(*cast("list[PathInput]", items))
    return [path(*cast("Iterable[PathInput]", i)) for i in items]


@vectorized
def path_file(path: str) -> FsPath:
    """Return the file name — the last path component.

    Vectorized: also accepts an iterable or pandas Series of paths.

    See Also
    --------
    path_dir : The complementary directory part.
    FsPath.name : Fluent equivalent.

    Examples
    --------
    >>> path_file("a/b/c.txt")
    FsPath('c.txt')
    """
    return FsPath(os.path.basename(tidy(path)))


@vectorized
def path_dir(path: str) -> FsPath:
    """Return the directory part of a path (``'.'`` if there is none).

    Vectorized: also accepts an iterable or pandas Series of paths.

    See Also
    --------
    path_file : The complementary file-name part.
    FsPath.dir : Fluent equivalent.

    Examples
    --------
    >>> path_dir("a/b/c.txt")
    FsPath('a/b')
    >>> path_dir("c.txt")
    FsPath('.')
    """
    return FsPath(os.path.dirname(tidy(path)) or ".")


@vectorized
def path_ext(path: str) -> str:
    """Return the extension without the dot (``''`` if none).

    Dotfiles like ``.gitignore`` count as having no extension. Vectorized:
    also accepts an iterable or pandas Series of paths.

    See Also
    --------
    path_ext_set, path_ext_remove

    Examples
    --------
    >>> path_ext("a.tar.gz")
    'gz'
    >>> path_ext(".gitignore")
    ''
    """
    return os.path.splitext(tidy(path))[1].lstrip(".")


@vectorized
def path_ext_remove(path: str) -> FsPath:
    """Remove the extension (dotfiles like ``.gitignore`` are left intact).

    Vectorized: also accepts an iterable or pandas Series of paths.

    Examples
    --------
    >>> path_ext_remove("d/a.tar.gz")
    FsPath('d/a.tar')
    """
    return FsPath(os.path.splitext(tidy(path))[0])


@vectorized
def path_ext_set(path: str, ext: str) -> FsPath:
    """Replace (or add) the extension; an empty `ext` removes it.

    Vectorized: also accepts an iterable or pandas Series of paths.

    Parameters
    ----------
    path : str or os.PathLike
        The path to modify.
    ext : str
        New extension, with or without the leading dot; ``""`` removes the
        current extension.

    See Also
    --------
    FsPath.with_ext : Fluent equivalent.

    Examples
    --------
    >>> path_ext_set("report.md", "html")
    FsPath('report.html')
    >>> path_ext_set(["a.txt", "b"], "py")
    [FsPath('a.py'), FsPath('b.py')]
    """
    root, _ = os.path.splitext(tidy(path))
    if not ext:
        return FsPath(root)
    return FsPath(f"{root}.{ext.lstrip('.')}")


def path_common(paths: Iterable[PathInput]) -> FsPath:
    """Return the longest common path prefix of `paths`.

    Parameters
    ----------
    paths : iterable of str or os.PathLike
        At least one path; all absolute or all relative.

    Raises
    ------
    FsValueError
        If `paths` is empty or mixes absolute and relative paths.

    Examples
    --------
    >>> path_common(["a/b/c", "a/b/d"])
    FsPath('a/b')
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
        Wildcard pattern matched against the whole path (e.g. ``"*.py"``);
        mutually exclusive with `regexp`.
    regexp : str, optional
        Regular expression searched within the path; mutually exclusive
        with `glob`.
    invert : bool, optional
        Keep the paths that do *not* match.

    Raises
    ------
    FsValueError
        If both `glob` and `regexp` are set.

    See Also
    --------
    pyrfs.dir_ls : Directory listing with the same filter arguments.

    Examples
    --------
    >>> path_filter(["a.py", "b.txt", "src/c.py"], glob="*.py")
    [FsPath('a.py'), FsPath('src/c.py')]
    >>> path_filter(["a.py", "b.txt"], glob="*.py", invert=True)
    [FsPath('b.txt')]
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
    and absolute forms compare consistently. Vectorized: also accepts an
    iterable or pandas Series of paths.

    See Also
    --------
    path_rel : Compute the relative path instead of testing containment.

    Examples
    --------
    >>> path_has_parent("/x/y", "/x")
    True
    >>> path_has_parent("/xy/z", "/x")
    False
    """
    child_parts = _abs_parts(path)
    parent_parts = _abs_parts(os.fspath(parent))
    return child_parts[: len(parent_parts)] == parent_parts


@vectorized
def path_sanitize(filename: str, replacement: str = "") -> str:
    """Turn an untrusted string into a filename safe on all major OSes.

    Removes control characters, characters illegal in filenames
    (``/\\?<>:*|"``), trailing dots/spaces, and Windows-reserved device
    names; truncates to 255 characters. Operates on a *filename*, not a
    path — separators are stripped, not preserved.

    Parameters
    ----------
    filename : str
        The untrusted string.
    replacement : str, optional
        What to substitute for removed characters (default: nothing).

    Examples
    --------
    >>> path_sanitize("rep/ort:2026*")
    'report2026'
    >>> path_sanitize("a/b", "_")
    'a_b'
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
