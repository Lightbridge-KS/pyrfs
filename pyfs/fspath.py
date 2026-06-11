"""``FsPath`` — a tidy path that *is* a ``str``, with chainable path methods.

Because ``FsPath`` subclasses ``str`` it drops into any API expecting a path
string (``open()``, ``pd.read_csv()``, ``os.fspath()``) with no conversion.
All path logic delegates to ``pyfs._engine`` — one engine, three surfaces.
"""

from __future__ import annotations

import os
import pathlib
from collections.abc import Iterable, Iterator

from pyfs.display import tidy
from pyfs.values import Bytes

__all__ = ["FsPath"]


class FsPath(str):
    """A tidy filesystem path string.

    Construction normalizes the path (``/`` separators, no doubled or
    trailing slashes). The ``/`` operator joins; methods chain because each
    returns an ``FsPath``. Inherited ``str`` behavior is untouched —
    ``p.split("/")``, ``p.startswith(...)`` etc. work as on any string.

    Examples
    --------
    >>> (FsPath("foo") / "bar" / "a.txt").with_ext("md")
    FsPath('foo/bar/a.md')
    """

    __slots__ = ()

    def __new__(cls, path: str | os.PathLike[str] = "") -> FsPath:
        return super().__new__(cls, tidy(path))

    def __truediv__(self, other: str | os.PathLike[str]) -> FsPath:
        """Join with `other`: ``FsPath('a') / 'b'`` -> ``FsPath('a/b')``."""
        return _paths.path(self, other)

    def __rtruediv__(self, other: str | os.PathLike[str]) -> FsPath:
        """Support ``'a' / FsPath('b')`` joining from a plain string."""
        return _paths.path(other, self)

    def __repr__(self) -> str:
        return f"FsPath({str.__repr__(self)})"

    # -- pure path algebra (no I/O) --------------------------------------
    def ext(self) -> str:
        """Extension without the dot (``''`` if none)."""
        return _paths.path_ext(self)

    def with_ext(self, ext: str) -> FsPath:
        """Replace (or add) the extension; ``''`` removes it."""
        return _paths.path_ext_set(self, ext)

    def dir(self) -> FsPath:
        """Directory part of the path (``'.'`` if there is none)."""
        return _paths.path_dir(self)

    def name(self) -> FsPath:
        """File name — the last path component."""
        return _paths.path_file(self)

    def parts(self) -> list[str]:
        """Path components (a leading root stays ``'/'``)."""
        return _paths.path_split(self)

    def rel_to(self, start: str | os.PathLike[str]) -> FsPath:
        """This path expressed relative to `start`."""
        return _paths.path_rel(self, start)

    def has_parent(self, parent: str | os.PathLike[str]) -> bool:
        """Whether this path sits at or below `parent`."""
        return _paths.path_has_parent(self, parent)

    def expand(self) -> FsPath:
        """Expand a leading ``~`` to the home directory."""
        return _paths.path_expand(self)

    def norm(self) -> FsPath:
        """Normalize ``.`` and ``..`` lexically."""
        return _paths.path_norm(self)

    # -- resolution against the running process --------------------------
    def abs(self) -> FsPath:
        """Absolute form (against the working directory); links unresolved."""
        return _paths.path_abs(self)

    def real(self) -> FsPath:
        """Canonical form with symlinks resolved (touches the filesystem)."""
        return _paths.path_real(self)

    # -- file verbs (I/O) -------------------------------------------------
    def copy_to(self, new_path: str | os.PathLike[str], *, overwrite: bool = False) -> FsPath:
        """Copy this file to `new_path` (file name or existing directory)."""
        return _fileops.file_copy(self, new_path, overwrite=overwrite)

    def move_to(self, new_path: str | os.PathLike[str], *, overwrite: bool = False) -> FsPath:
        """Move (rename) this file or directory to `new_path`."""
        return _fileops.file_move(self, new_path, overwrite=overwrite)

    def create(self, *, mode: int | str = 0o644) -> FsPath:
        """Create this file (left unchanged if it already exists)."""
        return _fileops.file_create(self, mode=mode)

    def touch(self) -> FsPath:
        """Update timestamps, creating the file if needed."""
        return _fileops.file_touch(self)

    def delete(self) -> None:
        """Delete this file or symlink."""
        _fileops.file_delete(self)

    def exists(self) -> bool:
        """Whether this path exists (broken symlinks count)."""
        return _fileops.file_exists(self)

    def access(self, mode: str = "exists") -> bool:
        """Test access: ``"exists"``, ``"read"``, ``"write"``, ``"execute"``."""
        return _fileops.file_access(self, mode)

    def size(self) -> Bytes:
        """File size as a :class:`~pyfs.Bytes` value."""
        return _fileops.file_size(self)

    def chmod(self, mode: int | str) -> FsPath:
        """Change permissions (symbolic modes apply to the current mode)."""
        return _fileops.file_chmod(self, mode)

    def info(self) -> dict[str, object]:
        """Stat this path into a row of typed values."""
        return _fileops.file_info(self)[0]

    # -- directory verbs (I/O) ---------------------------------------------
    def mkdir(self, *, mode: int | str = 0o755, recurse: bool = True) -> FsPath:
        """Create this directory (parents too when `recurse`); chains."""
        return _dirops.dir_create(self, mode=mode, recurse=recurse)

    def rmdir(self) -> None:
        """Delete this directory and everything below it (recursive)."""
        _dirops.dir_delete(self)

    def touch_file(self, name: str | os.PathLike[str]) -> FsPath:
        """Create a child file and return *this directory* (keeps chaining)."""
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
        """List entries of this directory (same filters as ``dir_ls``)."""
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
        """Lazily yield entries below this directory (recursive by default)."""
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
        """Print a box-drawing tree of this directory."""
        _dirops.dir_tree(self, recurse=recurse, all=all)

    # -- type predicates ----------------------------------------------------
    def is_file(self) -> bool:
        """Whether this path is a regular file (symlinks answer ``False``)."""
        return _predicates.is_file(self)

    def is_dir(self) -> bool:
        """Whether this path is a directory (symlinks answer ``False``)."""
        return _predicates.is_dir(self)

    def is_link(self) -> bool:
        """Whether this path is a symlink."""
        return _predicates.is_link(self)

    # -- interop ----------------------------------------------------------
    def as_pathlib(self) -> pathlib.Path:
        """This path as a ``pathlib.Path`` (for pathlib semantics)."""
        return pathlib.Path(self)


# Imported at the bottom to break the FsPath <-> engine import cycle:
# the engine returns FsPath; FsPath methods delegate to the engine.
from pyfs._engine import dirops as _dirops  # noqa: E402
from pyfs._engine import fileops as _fileops  # noqa: E402
from pyfs._engine import paths as _paths  # noqa: E402
from pyfs._engine import predicates as _predicates  # noqa: E402
