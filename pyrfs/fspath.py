"""``FsPath`` — a tidy path that *is* a ``str``, with chainable path methods.

Because ``FsPath`` subclasses ``str`` it drops into any API expecting a path
string (``open()``, ``pd.read_csv()``, ``os.fspath()``) with no conversion.
All path logic delegates to ``pyrfs._engine`` — one engine, three surfaces.
"""

from __future__ import annotations

import os
import pathlib
from collections.abc import Iterable, Iterator

from pyrfs.display import colourise_path, tidy
from pyrfs.values import Bytes

__all__ = ["FsPath"]


class FsPath(str):
    """A tidy filesystem path string — the fluent pyrfs surface.

    Construction normalizes the path (``/`` separators, no doubled or
    trailing slashes). The ``/`` operator joins; methods chain because each
    returns an ``FsPath``. Inherited ``str`` behavior is untouched —
    ``p.split("/")``, ``p.startswith(...)``, ``open(p)`` all work as on any
    string (the *split-into-components* method is `parts`, so ``str.split``
    is never shadowed). In a capable terminal the repr is coloured by
    on-disk type via ``LS_COLORS``.

    See Also
    --------
    pyrfs.path : Functional construction with an ``ext=`` option.
    as_pathlib : Convert when you want ``pathlib`` semantics.

    Examples
    --------
    >>> FsPath("src//a.txt/")  # tidied on construction
    FsPath('src/a.txt')
    >>> (FsPath("foo") / "bar" / "a.txt").with_ext("md")
    FsPath('foo/bar/a.md')
    >>> FsPath("a/b").startswith("a")  # still a str
    True
    """

    __slots__ = ()

    def __new__(cls, path: str | os.PathLike[str] = "") -> FsPath:
        return super().__new__(cls, tidy(path))

    def __truediv__(self, other: str | os.PathLike[str]) -> FsPath:
        """Join with `other`: ``FsPath('a') / 'b'`` -> ``FsPath('a/b')``.

        Concatenation + tidy: an absolute right-hand side does *not* reset
        the path (unlike ``pathlib``/``os.path.join``).
        """
        return _paths.path(self, other)

    def __rtruediv__(self, other: str | os.PathLike[str]) -> FsPath:
        """Support ``'a' / FsPath('b')`` joining from a plain string."""
        return _paths.path(other, self)

    def __repr__(self) -> str:
        # coloured by on-disk type via LS_COLORS; plain on non-TTY / NO_COLOR
        return f"FsPath({colourise_path(self, str.__repr__(self))})"

    # -- pure path algebra (no I/O) --------------------------------------
    def ext(self) -> str:
        """Extension without the dot (``''`` if none) — `pyrfs.path_ext`."""
        return _paths.path_ext(self)

    def with_ext(self, ext: str) -> FsPath:
        """Replace (or add) the extension; ``''`` removes it — `pyrfs.path_ext_set`.

        Examples
        --------
        >>> (FsPath("data") / "raw.csv").with_ext("parquet")
        FsPath('data/raw.parquet')
        """
        return _paths.path_ext_set(self, ext)

    def dir(self) -> FsPath:
        """Directory part of the path (``'.'`` if none) — `pyrfs.path_dir`."""
        return _paths.path_dir(self)

    def name(self) -> FsPath:
        """File name — the last path component — `pyrfs.path_file`."""
        return _paths.path_file(self)

    def parts(self) -> list[str]:
        """Path components (a leading root stays ``'/'``) — `pyrfs.path_split`.

        Named ``parts`` (as in ``pathlib``) so ``str.split`` keeps its
        normal string behavior.

        Examples
        --------
        >>> FsPath("/usr/bin").parts()
        ['/', 'usr', 'bin']
        """
        return _paths.path_split(self)

    def rel_to(self, start: str | os.PathLike[str]) -> FsPath:
        """This path expressed relative to `start` — `pyrfs.path_rel`."""
        return _paths.path_rel(self, start)

    def has_parent(self, parent: str | os.PathLike[str]) -> bool:
        """Whether this path sits at or below `parent` — `pyrfs.path_has_parent`."""
        return _paths.path_has_parent(self, parent)

    def expand(self) -> FsPath:
        """Expand a leading ``~`` to the home directory — `pyrfs.path_expand`."""
        return _paths.path_expand(self)

    def norm(self) -> FsPath:
        """Normalize ``.`` and ``..`` lexically — `pyrfs.path_norm`."""
        return _paths.path_norm(self)

    # -- resolution against the running process --------------------------
    def abs(self) -> FsPath:
        """Absolute form (links unresolved) — `pyrfs.path_abs`."""
        return _paths.path_abs(self)

    def real(self) -> FsPath:
        """Canonical form, symlinks resolved — `pyrfs.path_real`."""
        return _paths.path_real(self)

    # -- file verbs (I/O) -------------------------------------------------
    def copy_to(self, new_path: str | os.PathLike[str], *, overwrite: bool = False) -> FsPath:
        """Copy this file to `new_path` — `pyrfs.file_copy`.

        Copying into an existing directory targets ``new_path/basename``;
        an existing destination raises ``FileExistsError`` unless
        ``overwrite=True``. Returns the new copy's path (chains).
        """
        return _fileops.file_copy(self, new_path, overwrite=overwrite)

    def move_to(self, new_path: str | os.PathLike[str], *, overwrite: bool = False) -> FsPath:
        """Move (rename) this file or directory — `pyrfs.file_move`.

        Same destination resolution and ``overwrite`` guard as `copy_to`.
        """
        return _fileops.file_move(self, new_path, overwrite=overwrite)

    def create(self, *, mode: int | str = 0o644) -> FsPath:
        """Create this file (existing files untouched) — `pyrfs.file_create`."""
        return _fileops.file_create(self, mode=mode)

    def touch(self) -> FsPath:
        """Update timestamps, creating the file if needed — `pyrfs.file_touch`."""
        return _fileops.file_touch(self)

    def delete(self) -> None:
        """Delete this file or symlink — `pyrfs.file_delete`.

        Returns ``None``: a deleted path has nothing to chain onto.
        For directories use `rmdir`.
        """
        _fileops.file_delete(self)

    def exists(self) -> bool:
        """Whether this path exists (broken symlinks count) — `pyrfs.file_exists`."""
        return _fileops.file_exists(self)

    def access(self, mode: str = "exists") -> bool:
        """Test ``"exists"``/``"read"``/``"write"``/``"execute"`` — `pyrfs.file_access`."""
        return _fileops.file_access(self, mode)

    def size(self) -> Bytes:
        """File size as a `pyrfs.Bytes` value — `pyrfs.file_size`.

        Examples
        --------
        >>> FsPath("notes.txt").create().size() == 0
        True
        """
        return _fileops.file_size(self)

    def chmod(self, mode: int | str) -> FsPath:
        """Change permissions — `pyrfs.file_chmod`.

        Symbolic modes (``"u+x"``) apply to the *current* mode; octal and
        display forms are absolute. Returns this path (chains).
        """
        return _fileops.file_chmod(self, mode)

    def info(self) -> dict[str, object]:
        """Stat this path into one row of typed values — `pyrfs.file_info`.

        Returns a single ``dict`` (use the functional `pyrfs.file_info` /
        `pyrfs.dir_info` for tables).
        """
        return _fileops.file_info(self)[0]

    # -- directory verbs (I/O) ---------------------------------------------
    def mkdir(self, *, mode: int | str = 0o755, recurse: bool = True) -> FsPath:
        """Create this directory (parents too when `recurse`) — `pyrfs.dir_create`.

        Examples
        --------
        >>> FsPath("proj").mkdir().touch_file("README.md").ls()
        [FsPath('proj/README.md')]
        """
        return _dirops.dir_create(self, mode=mode, recurse=recurse)

    def rmdir(self) -> None:
        """Delete this directory and everything below it — `pyrfs.dir_delete`.

        Recursive (``rm -rf`` semantics), despite the ``os.rmdir``-like
        name. Returns ``None``: nothing left to chain onto.
        """
        _dirops.dir_delete(self)

    def touch_file(self, name: str | os.PathLike[str]) -> FsPath:
        """Create a child file and return *this directory* (keeps chaining).

        Returning the directory (not the new file) lets several
        ``touch_file`` calls chain; use ``(p / name).touch()`` when you
        want the file's path back.
        """
        _fileops.file_touch(self / name)
        return self

    def ls(
        self,
        *,
        all: bool = False,
        recurse: bool | int = False,
        type: str | Iterable[str] = "any",
        glob: str | None = None,
        regexp: str | None = None,
        invert: bool = False,
        fail: bool = True,
    ) -> list[FsPath]:
        """List entries of this directory — `pyrfs.dir_ls` (same filters)."""
        return _dirops.dir_ls(
            self,
            all=all,
            recurse=recurse,
            type=type,
            glob=glob,
            regexp=regexp,
            invert=invert,
            fail=fail,
        )

    def walk(
        self,
        *,
        all: bool = False,
        recurse: bool | int = True,
        type: str | Iterable[str] = "any",
        glob: str | None = None,
        regexp: str | None = None,
        invert: bool = False,
        fail: bool = True,
    ) -> Iterator[FsPath]:
        """Lazily yield entries below this directory — `pyrfs.dir_walk`.

        Unlike the functional default, ``recurse=True`` here: walking a
        tree is the common fluent use.
        """
        return _dirops.dir_walk(
            self,
            all=all,
            recurse=recurse,
            type=type,
            glob=glob,
            regexp=regexp,
            invert=invert,
            fail=fail,
        )

    def tree(self, *, recurse: bool | int = True, all: bool = False) -> None:
        """Print a box-drawing tree of this directory — `pyrfs.dir_tree`."""
        _dirops.dir_tree(self, recurse=recurse, all=all)

    # -- type predicates ----------------------------------------------------
    def is_file(self) -> bool:
        """Whether this is a regular file (lstat; symlinks answer ``False``) — `pyrfs.is_file`."""
        return _predicates.is_file(self)

    def is_dir(self) -> bool:
        """Whether this is a directory (lstat; symlinks answer ``False``) — `pyrfs.is_dir`."""
        return _predicates.is_dir(self)

    def is_link(self) -> bool:
        """Whether this is a symlink — `pyrfs.is_link`."""
        return _predicates.is_link(self)

    # -- interop ----------------------------------------------------------
    def as_pathlib(self) -> pathlib.Path:
        """This path as a ``pathlib.Path``, when you want pathlib semantics.

        Examples
        --------
        >>> FsPath("a/b").as_pathlib()
        PosixPath('a/b')
        """
        return pathlib.Path(self)


# Imported at the bottom to break the FsPath <-> engine import cycle:
# the engine returns FsPath; FsPath methods delegate to the engine.
from pyrfs._engine import dirops as _dirops  # noqa: E402
from pyrfs._engine import fileops as _fileops  # noqa: E402
from pyrfs._engine import paths as _paths  # noqa: E402
from pyrfs._engine import predicates as _predicates  # noqa: E402
