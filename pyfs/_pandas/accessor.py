"""The ``Series.fs`` accessor — vectorized pyfs operations over a path column.

Each method delegates to the engine (whose ``@vectorized`` functions already
map over a Series), then types the result column: paths -> ``"path"`` dtype,
sizes -> ``"bytes"``, predicates -> ``bool``.
"""

from __future__ import annotations

import pandas as pd
from pandas.api.extensions import register_series_accessor

from pyfs._engine import fileops as _fileops
from pyfs._engine import paths as _paths
from pyfs._engine import predicates as _predicates
from pyfs._engine.vectorize import PathInput

__all__ = ["FsSeriesAccessor"]


@register_series_accessor("fs")
class FsSeriesAccessor:
    """Vectorized path operations: ``df["path"].fs.ext()`` etc."""

    def __init__(self, series: pd.Series) -> None:
        self._series = series

    # -- path algebra (no I/O) ----------------------------------------------
    def ext(self) -> pd.Series:
        """Extension of each path (without the dot)."""
        return _paths.path_ext(self._series)

    def with_ext(self, ext: str) -> pd.Series:
        """Replace (or add) the extension of each path."""
        return _paths.path_ext_set(self._series, ext).astype("path")

    def ext_remove(self) -> pd.Series:
        """Each path without its extension."""
        return _paths.path_ext_remove(self._series).astype("path")

    def dir(self) -> pd.Series:
        """Directory part of each path."""
        return _paths.path_dir(self._series).astype("path")

    def name(self) -> pd.Series:
        """File name (last component) of each path."""
        return _paths.path_file(self._series).astype("path")

    def norm(self) -> pd.Series:
        """Each path with ``.``/``..`` normalized lexically."""
        return _paths.path_norm(self._series).astype("path")

    def expand(self) -> pd.Series:
        """Each path with a leading ``~`` expanded."""
        return _paths.path_expand(self._series).astype("path")

    def abs(self) -> pd.Series:
        """Absolute form of each path."""
        return _paths.path_abs(self._series).astype("path")

    def real(self) -> pd.Series:
        """Canonical form of each path (symlinks resolved)."""
        return _paths.path_real(self._series).astype("path")

    def rel_to(self, start: PathInput) -> pd.Series:
        """Each path expressed relative to `start`."""
        return _paths.path_rel(self._series, start).astype("path")

    def has_parent(self, parent: PathInput) -> pd.Series:
        """Whether each path sits at or below `parent`."""
        return _paths.path_has_parent(self._series, parent).astype(bool)

    # -- filesystem queries (I/O) ---------------------------------------------
    def exists(self) -> pd.Series:
        """Whether each path exists (broken symlinks count)."""
        return _fileops.file_exists(self._series).astype(bool)

    def is_file(self) -> pd.Series:
        """Whether each path is a regular file."""
        return _predicates.is_file(self._series).astype(bool)

    def is_dir(self) -> pd.Series:
        """Whether each path is a directory."""
        return _predicates.is_dir(self._series).astype(bool)

    def is_link(self) -> pd.Series:
        """Whether each path is a symlink."""
        return _predicates.is_link(self._series).astype(bool)

    def size(self) -> pd.Series:
        """Size of each file as a ``bytes``-dtype column."""
        return _fileops.file_size(self._series).astype("bytes")
