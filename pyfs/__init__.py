"""pyfs — Pythonic filesystem ergonomics inspired by R's fs.

Tidy paths, typed self-describing values, chainable operations, and
optional pandas integration. See https://github.com/Lightbridge-KS/pyfs.
"""

import contextlib

from pyfs._engine.dirops import (
    dir_copy,
    dir_create,
    dir_delete,
    dir_exists,
    dir_ls,
    dir_map,
    dir_tree,
    dir_walk,
)
from pyfs._engine.fileops import (
    file_access,
    file_chmod,
    file_chown,
    file_copy,
    file_create,
    file_delete,
    file_exists,
    file_move,
    file_show,
    file_size,
    file_touch,
)
from pyfs._engine.ids import group_ids, user_ids
from pyfs._engine.linkops import (
    link_copy,
    link_create,
    link_delete,
    link_exists,
    link_path,
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
from pyfs._engine.predicates import (
    is_absolute_path,
    is_dir,
    is_dir_empty,
    is_file,
    is_file_empty,
    is_link,
)
from pyfs._engine.temp import file_temp, file_temp_pop, file_temp_push
from pyfs.errors import FsError, FsValueError
from pyfs.fspath import FsPath
from pyfs.info import dir_info, file_info, has_pandas
from pyfs.values import Bytes, Perms

__version__ = "0.1.0"

__all__ = [
    "Bytes",
    "FsError",
    "FsPath",
    "FsValueError",
    "Perms",
    "__version__",
    "dir_copy",
    "dir_create",
    "dir_delete",
    "dir_exists",
    "dir_info",
    "dir_ls",
    "dir_map",
    "dir_tree",
    "dir_walk",
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
    "group_ids",
    "has_pandas",
    "is_absolute_path",
    "is_dir",
    "is_dir_empty",
    "is_file",
    "is_file_empty",
    "is_link",
    "link_copy",
    "link_create",
    "link_delete",
    "link_exists",
    "link_path",
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
    "user_ids",
]

# Optional pandas layer: importing it registers the dtypes and the Series.fs
# accessor; without pandas installed the core works unchanged.
with contextlib.suppress(ImportError):
    import pyfs._pandas  # noqa: F401
