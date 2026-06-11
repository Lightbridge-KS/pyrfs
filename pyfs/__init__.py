"""pyfs — Pythonic filesystem ergonomics inspired by R's fs.

Tidy paths, typed self-describing values, chainable operations, and
optional pandas integration. See https://github.com/Lightbridge-KS/pyfs.
"""

from pyfs._engine.paths import (
    path,
    path_abs,
    path_common,
    path_dir,
    path_expand,
    path_ext,
    path_ext_remove,
    path_ext_set,
    path_file,
    path_filter,
    path_has_parent,
    path_home,
    path_join,
    path_norm,
    path_real,
    path_rel,
    path_sanitize,
    path_split,
    path_temp,
    path_tidy,
    path_wd,
)
from pyfs.errors import FsError, FsValueError
from pyfs.fspath import FsPath

__version__ = "0.1.0"

__all__ = [
    "FsError",
    "FsPath",
    "FsValueError",
    "__version__",
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
