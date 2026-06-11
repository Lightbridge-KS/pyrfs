# pyfs — Implementation Progress

> Build tracker for **pyfs** (Pythonic port of R's `fs`). Design: [`pyfs-architecture.md`](./pyfs-architecture.md) · [`pyfs-ux.md`](./pyfs-ux.md)
> Legend: `[ ]` todo · `[~]` in progress · `[x]` done · Status updated: 2026-06-11

## Status snapshot

| Phase | Title | State |
|-------|-------|-------|
| P0 | Project scaffold | `[x]` |
| P1 | Path algebra + `FsPath` | `[x]` |
| P2 | Typed scalars (`Bytes`, `Perms`) | `[x]` |
| P3 | File ops + errors + temp | `[x]` |
| P4 | Dir + link + ids | `[ ]` |
| P5 | pandas layer | `[ ]` |
| P6 | Display, docs, packaging | `[ ]` |

Guiding rules: tight feedback loops (test after each change); `mypy --strict` clean, no `Any`;
NumPy-style docstrings on public API; public methods before private; `_engine` never imports pandas.

---

## P0 — Project scaffold
- [x] `uv init`; `pyproject.toml` with setuptools backend, `requires-python = ">=3.10"`
- [x] Flat layout: package at `pyfs/pyfs/`; `[tool.setuptools.packages.find] where=["."] include=["pyfs*"]`
- [x] Optional deps: `pandas`, `dev = [pytest, ruff, mypy]` (dependency-group; `color` extra deferred to P6)
- [x] Tooling config: `ruff` (lint+format), `mypy` (strict), `pytest`
- [x] Ship `pyfs/py.typed`; `pyfs/__init__.py` with `__version__`
- [x] `tests/` dir + a trivial `test_import.py`
- [x] CI workflow (lint + type + test matrix; with and without `[pandas]`)
- **Gate:** `uv run pytest`, `uv run mypy --strict pyfs`, `uv run ruff check` all green.

## P1 — Path algebra + `FsPath`
- [x] `display.tidy()` — normalize to `/`, collapse `//`, strip trailing `/`, UTF-8
- [x] `_engine/paths.py`: `path`, `path_wd`, `path_abs`, `path_real`, `path_norm`, `path_rel`,
      `path_split`, `path_join`, `path_file`, `path_dir`, `path_ext`, `path_ext_remove`,
      `path_ext_set`, `path_common`, `path_filter`, `path_has_parent`, `path_expand`,
      `path_home`, `path_sanitize`, `path_tidy`, `path_temp`
- [x] `fspath.py`: `FsPath(str)` — `__truediv__`/`__rtruediv__`, `with_ext`, `ext`, `dir`, `name`,
      `abs`, `real`, `norm`, `expand`, `rel_to`, `has_parent`, `parts`, `as_pathlib`;
      delegates to `_engine/paths`
- [x] `_engine/vectorize.py`: `@vectorized` (scalar | list | Series dispatch)
- [x] Tests: tidy edge cases, ext round-trips, `path_rel`/`path_common`, vectorized inputs
- **Gate:** path algebra fully covered; `FsPath("a") / "b"` and chains work. ✅
- Notes: fluent split is named `parts()` (overriding `str.split` would break str interop);
  `path_expand_r`/`path_home_r` dropped (no R-vs-libuv distinction in Python);
  `path_select_components` + `path_package` deferred → parking lot.

## P2 — Typed scalars
- [x] `display.py`: `humanize_bytes`, `parse_bytes` (`"10MB"`, `"1.5GiB"`), `perms_to_str`,
      `parse_perms` (octal `"644"`, symbolic `"u+rw,go+r"`, display `"rw-r--r--"`)
- [x] `values.py`: `Bytes(int)` — construct from str/int, `repr/str/__format__`, comparison vs
      string, arithmetic returns `Bytes` (incl. `sum()` via `__radd__`)
- [x] `values.py`: `Perms(int)` — construct from octal/symbolic/int, `repr` → rwx, `& | ^ ~`
      return `Perms`, `==` parses string
- [x] Tests: parse/format round-trips, comparisons, operator results, edge units
- **Gate:** `Bytes("10MB") < "1GB"`, `Perms("644") == "rw-r--r--"` behave as specified. ✅
- Notes: all byte units are 1024-based matching R fs (`"10MB"` == `"10MiB"`);
  `Bytes.__repr__` stays exact (`Bytes(455200)`), `str()`/`format()` humanize;
  `Perms.__repr__` shows rwx form (round-trips exactly).

## P3 — File ops + errors + temp
- [x] `errors.py`: `FsError(Exception)` + `FsValueError` (landed early in P1)
- [x] `_engine/fileops.py`: `file_create`, `file_copy`, `file_move`, `file_delete`, `file_touch`,
      `file_show`, `file_access`, `file_exists`, `file_size` (→`Bytes`), `file_chmod`, `file_chown`,
      `file_info` (→`list[dict]` of typed rows; DataFrame upgrade in P5)
- [x] Safe defaults: `overwrite=False` → `FileExistsError`; keyword-only flags;
      copy/move into an existing dir targets `dir/basename`
- [x] `_engine/temp.py`: `file_temp` (+ deterministic FIFO push/pop stack); `path_temp` in paths
- [x] `FsPath` verb methods: `copy_to`, `move_to`, `create`, `touch`, `delete`, `size`, `chmod`,
      `exists`, `access`, `info`
- [x] Tests in `tmp_path`: copy/move/delete round-trips, overwrite guard, temp stack determinism
- **Gate:** file lifecycle works via functional + fluent surfaces; failures raise correctly. ✅
- Notes: `file_exists` uses `lexists` (broken symlink counts, matching fs);
  `file_chmod` applies symbolic modes relative to the current mode (chmod semantics).

## P4 — Dir + link + ids
- [ ] `_engine/dirops.py`: `dir_create` (`recurse=True`), `dir_copy`, `dir_delete`, `dir_exists`,
      `dir_ls` (filters: `all`, `recurse:int|bool`, `type`, `glob`/`regexp`, `invert`, `fail`),
      `dir_map`, `dir_walk`, `dir_tree` (box-drawing)
- [ ] `_engine/linkops.py`: `link_create` (`symbolic=True`), `link_copy`, `link_delete`,
      `link_exists`, `link_path`
- [ ] `_engine/ids.py`: `user_ids`, `group_ids` (POSIX via `pwd`/`grp`; empty on Windows)
- [ ] predicates: `is_file`, `is_dir`, `is_link`, `is_file_empty`, `is_dir_empty`, `is_absolute_path`
- [ ] `FsPath`: `ls`, `walk`, `tree`, `mkdir`, `rmdir`
- [ ] Tests: recursion depth, type/glob filters, `fail=False` warning path, symlink round-trip
- **Gate:** directory traversal + filtering + links match `fs` semantics.

## P5 — pandas layer (optional extra)
- [ ] `_pandas/dtypes.py` + `arrays.py`: `BytesDtype/Array`, `PermsDtype/Array`, `PathDtype/Array`
      (`_from_sequence`, `__getitem__`, `__len__`, `isna`, `take`, `copy`, `_concat_same_type`,
      `ExtensionScalarOpsMixin`, `@register_extension_dtype`); reuse `display.py`/`values.py`
- [ ] `_pandas/frames.py`: build `file_info`/`dir_info` DataFrames with typed columns
- [ ] `_pandas/accessor.py`: `@register_series_accessor("fs")` → `ext/dir/name/abs/exists/is_dir/with_ext`
- [ ] `__init__.py`: lazy `try: import pyfs._pandas`; `has_pandas()`; `*_info` → DataFrame else `list[dict]`
- [ ] Tests guarded by `importorskip("pandas")`; verify `dir_info().query("size > '10KB'")`,
      accessor ops, reductions; run suite **with and without** the extra
- **Gate:** headline demo works; core suite passes when pandas absent.

## P6 — Display, docs, packaging
- [ ] `display.py`: `LS_COLORS` colouriser for `FsPath.__repr__`; degrade on non-TTY/`NO_COLOR`
- [ ] `dir_tree` colour; multicolumn path printing (optional)
- [ ] README with quickstart; docstring pass (NumPy style) on all public API
- [ ] `examples/` notebook: the three surfaces + pandas pipe workflow
- [ ] Build sdist+wheel (`uv build`); smoke-install in clean venv (core only, then `[pandas]`)
- [ ] Publish to **TestPyPI** first; tag release
- **Gate:** clean install both flavors; docs render; examples run top-to-bottom.

---

## Cross-phase definition of done
- [ ] `uv run ruff check` + `uv run ruff format --check` clean
- [ ] `uv run mypy --strict pyfs` clean (no `Any`)
- [ ] `uv run pytest` green **with** and **without** the `[pandas]` extra
- [ ] Public API has NumPy-style docstrings + type annotations
- [ ] Smoke test: fluent copy/move/delete round-trip in a tmp dir + `dir_info().query(...)` demo

## Parking lot / later
- `path_select_components` and `path_package` (R-isms; revisit demand for Python equivalents).
- Check PyPI availability of the `pyfs` distribution name before P6 publish (import name stays `pyfs`).
- Async variants (`aiofiles`-backed) — out of scope for v1.
- Remote/cloud backends — explicit non-goal (use `fsspec`).
- Rich/`textual` integration for `dir_tree` — nice-to-have.
