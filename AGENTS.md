# pyfs — Agent Instructions

Pythonic port of R's [`fs`](https://fs.r-lib.org) UX: tidy paths, typed values
(`FsPath`/`Bytes`/`Perms`), chainable, pandas-friendly. Pure Python ≥ 3.10, stdlib-only core.

**Design docs (read before structural changes):** `docs/pyfs-ux.md` (API feel),
`docs/pyfs-architecture.md` (structure), `docs/PROGRESS.md` (master tracker — update its
checkboxes when you complete tracked work).

## Architecture invariants

- **One engine, three surfaces.** All logic lives in `pyfs/_engine/`; the functional API,
  `FsPath` methods, and the pandas `.fs` accessor are thin delegates. Never duplicate logic
  in a surface.
- **`pyfs/_engine/`, `values.py`, `display.py` never import pandas** (not even indirectly).
  `pyfs/_pandas/` depends inward on them, never the reverse. Optional registration happens in
  `pyfs/__init__.py` via `contextlib.suppress(ImportError)`.
- Engine `*_info` always returns `list[dict]`; the public surface (`pyfs/info.py`) upgrades
  to a typed DataFrame when pandas is present.
- `display.py` is the single source of truth for parse/format (bytes, perms, tidy, colour).
- Layout is flat: the package is `pyfs/` at repo root (no `src/`).

## Commands

```sh
uv sync                                  # core dev env
uv run ruff check && uv run ruff format --check
uv run mypy --strict pyfs                # must stay clean
uv run --extra pandas pytest             # full suite (pandas mode)
uv sync --exact && uv run --no-sync pytest   # core mode (prunes pandas first!)
```

Run **all of the above** before any commit. Caution: `uv run --extra pandas` leaves pandas
in `.venv`; a plain `uv run pytest` afterwards is NOT a core-mode run — prune with
`uv sync --exact` first.

## Conventions

- `mypy --strict`, no `Any` in the core package. pandas/numpy are opaque to mypy
  (`follow_imports = "skip"` in pyproject) so results are identical with/without the extra;
  only `pyfs._pandas.*` has narrow relaxations.
- NumPy-style docstrings on public API; public methods before private in classes.
- fs argument conventions: behavior flags keyword-only; safe defaults
  (`overwrite=False`, `recurse=False` for listing / `True` for `dir_create`, `all=False`,
  `fail=True`); `glob`/`regexp` mutually exclusive → `FsValueError`.
- Errors: native `OSError` subclasses for OS failures; `FsError`/`FsValueError` for
  pyfs-level validation only.
- Conventional Commits, committed directly to `main` (early phase); CI must be green.

## Semantics worth knowing (deliberate, don't "fix")

- `FsPath` subclasses `str` — never shadow `str` methods (the split method is `parts()`).
- `/` join is concatenation + tidy (an absolute RHS does **not** reset the path, unlike
  `os.path.join`).
- `Bytes` units are all 1024-based (`"10MB"` == `"10MiB"`), matching R fs.
- `is_file`/`is_dir` use lstat semantics: a symlink is only `is_link`.
- `file_exists` uses `lexists` (broken symlinks count). No `dir_move` — dirs move via
  `file_move`. `dir_copy`/`file_copy` into an existing dir resolve to `dir/basename`
  before the overwrite guard.
- Colour (`FsPath.__repr__`, `dir_tree`): `NO_COLOR` > `FORCE_COLOR` > TTY detection.
