# Changelog

All notable changes to **pyrfs** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Initial development toward **0.1.0** — a Pythonic port of the UX of R's
[fs](https://fs.r-lib.org) package.

### Added

- **Path algebra** (`path_*`, no I/O): `path()` with `ext=`, `path_dir`/
  `path_file`/`path_ext*`, `path_rel`, `path_common`, `path_filter`
  (glob/regexp, mutually exclusive), `path_split`/`path_join`,
  `path_has_parent`, `path_sanitize`, `path_expand`/`path_home`/`path_temp`,
  `path_tidy`.
- **`FsPath`** — a tidy path that subclasses `str`: `/` join operator,
  chainable methods delegating to the engine, `LS_COLORS`-coloured repr
  (degrades on non-TTY / `NO_COLOR`), `as_pathlib()` escape hatch.
- **Typed scalars**: `Bytes ⊂ int` (parses `"10MB"`, displays `444.5K`,
  compares against literals, arithmetic stays typed — all units 1024-based)
  and `Perms ⊂ int` (octal/symbolic/`rw-r--r--` forms, mode algebra).
- **File operations** (`file_*`): create/touch/copy/move/delete/exists/
  access/size/chmod/chown/show/info — mutating verbs return the new path;
  `overwrite=False` raises `FileExistsError`; copy/move into an existing
  directory targets `dir/basename`; symbolic chmod applies to the current
  mode.
- **Directory operations** (`dir_*`): create/copy/delete/exists, lazy
  `dir_walk` generator with the full fs filter set (`all`,
  `recurse: bool | int`, `type`, `glob`/`regexp`, `invert`,
  `fail=False` → warn-and-skip), `dir_ls`, `dir_map`, `dir_info`, and a
  box-drawing, coloured `dir_tree`. No `dir_move` by design — use
  `file_move`.
- **Link operations** (`link_*`): symbolic (default) and hard creation,
  `link_path`, `link_exists`, `link_copy`, `link_delete` (refuses
  non-links).
- **Predicates & ids**: `is_file`/`is_dir`/`is_link` (lstat semantics — a
  symlink is only `is_link`), `is_file_empty`, `is_dir_empty`,
  `is_absolute_path`; `user_ids`/`group_ids` (POSIX).
- **Vectorization**: every path-taking function is polymorphic over a
  scalar, list/tuple/set, or pandas Series (without the engine importing
  pandas).
- **pandas layer** (optional `[pandas]` extra): `bytes`/`perms`/`path`
  ExtensionDtypes lifting the scalar semantics onto columns
  (`size > "10KB"` works in `.query()`), the `Series.fs` accessor, and
  `file_info`/`dir_info` returning typed DataFrames (engine rows without
  pandas).
- **Temp helpers**: `file_temp` with a deterministic `file_temp_push`/`pop`
  stack for reproducible docs and tests.
- **Errors**: native `OSError` subclasses for OS failures; `FsError`/
  `FsValueError` for pyrfs-level validation.
- **Docs**: MkDocs Material site at <https://pyrfs.netlify.app> with
  llms.txt/llms-full.txt, an executed tour notebook, and a Quarto-rendered
  README kept fresh by CI.

[Unreleased]: https://github.com/Lightbridge-KS/pyrfs/commits/main
