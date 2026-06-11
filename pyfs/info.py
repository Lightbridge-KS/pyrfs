"""Public ``*_info`` surface — DataFrame when pandas is installed, rows otherwise.

The engine always produces ``list[dict]`` rows of typed scalars; this module
upgrades them to a typed DataFrame (``path``/``size``/``permissions`` columns
use the pyfs ExtensionDtypes) when pandas is available.
"""

from __future__ import annotations

import functools
from collections.abc import Iterable
from typing import TYPE_CHECKING

from pyfs._engine import dirops as _dirops
from pyfs._engine import fileops as _fileops
from pyfs._engine.vectorize import PathInput

if TYPE_CHECKING:
    import pandas as pd

__all__ = ["dir_info", "file_info", "has_pandas"]


@functools.cache
def has_pandas() -> bool:
    """Whether pandas is importable (cached; decides the ``*_info`` shape)."""
    try:
        import pandas  # noqa: F401
    except ImportError:
        return False
    return True


def file_info(
    path: PathInput | Iterable[PathInput], *, follow: bool = False
) -> pd.DataFrame | list[dict[str, object]]:
    """Stat path(s) into a typed table.

    Returns a DataFrame with typed columns (``path``/``size``/``permissions``
    as pyfs dtypes) when pandas is installed, else ``list[dict]`` rows.

    Examples
    --------
    >>> file_info("pyproject.toml")  # doctest: +SKIP
                 path  type    size permissions ...
    0  pyproject.toml  file    1.7K   rw-r--r-- ...
    """
    return _maybe_frame(_fileops.file_info(path, follow=follow))


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
) -> pd.DataFrame | list[dict[str, object]]:
    """Stat directory entries into a typed table (same filters as ``dir_ls``).

    Examples
    --------
    >>> (dir_info("pyfs", recurse=True)              # doctest: +SKIP
    ...     .query("size > '10KB' and type == 'file'")
    ...     .sort_values("size", ascending=False))
    """
    rows = _dirops.dir_info(
        path,
        all=all,
        recurse=recurse,
        type=type,
        glob=glob,
        regexp=regexp,
        invert=invert,
        fail=fail,
    )
    return _maybe_frame(rows)


def _maybe_frame(
    rows: list[dict[str, object]],
) -> pd.DataFrame | list[dict[str, object]]:
    if has_pandas():
        from pyfs._pandas.frames import info_frame

        return info_frame(rows)
    return rows
