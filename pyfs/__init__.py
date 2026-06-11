"""pyfs — Pythonic filesystem ergonomics inspired by R's fs.

Tidy paths, typed self-describing values, chainable operations, and
optional pandas integration. See https://github.com/Lightbridge-KS/pyfs.
"""

from pyfs._engine.fileops import (
    file_access,
    file_chmod,
    file_chown,
    file_copy,
    file_create,
    file_delete,
    file_exists,
    file_info,
    file_move,
    file_show,
    file_size,
    file_touch,
)
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
from pyfs._engine.temp import file_temp, file_temp_pop, file_temp_push
from pyfs.errors import FsError, FsValueError
from pyfs.fspath import FsPath
from pyfs.values import Bytes, Perms

__version__ = "0.1.0"

__all__ = [
    "Bytes",
    "FsError",
    "FsPath",
    "FsValueError",
    "Perms",
    "__version__",
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
    "file_temp",
    "file_temp_pop",
    "file_temp_push",
    "file_touch",
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
