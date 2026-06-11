# pyrfs — Agent Instructions

Pythonic port of R's [`fs`](https://fs.r-lib.org) UX: tidy paths, typed values
(`FsPath`/`Bytes`/`Perms`), chainable, pandas-friendly. Pure Python ≥ 3.10, stdlib-only core.

**Design docs (read before structural changes):** `docs/design/pyrfs-ux.md` (API feel),
`docs/design/pyrfs-architecture.md` (structure).

**README is generated:** never edit `README.md` directly — edit `README.qmd`, then render
with `uv run --group docs --extra pandas quarto render README.qmd` (Quarto executes the
code cells; temp paths are kept deterministic via `file_temp_push`). Commit both files.

**Docs site:** MkDocs Material (`mkdocs.yml`; content in `docs/`), deployed on Netlify
(https://pyrfs.netlify.app). Build locally with
`uv run --group docs --extra pandas mkdocs build --strict` — the tour notebook executes
during the build (it is symlinked from `examples/` into `docs/tour/`). API pages use
mkdocstrings `::: pyrfs.<name>` directives; new public API needs an entry in `docs/api/`.

## Architecture invariants

- **One engine, three surfaces.** All logic lives in `pyrfs/_engine/`; the functional API,
  `FsPath` methods, and the pandas `.fs` accessor are thin delegates. Never duplicate logic
  in a surface.
- **`pyrfs/_engine/`, `values.py`, `display.py` never import pandas** (not even indirectly).
  `pyrfs/_pandas/` depends inward on them, never the reverse. Optional registration happens in
  `pyrfs/__init__.py` via `contextlib.suppress(ImportError)`.
- Engine `*_info` always returns `list[dict]`; the public surface (`pyrfs/info.py`) upgrades
  to a typed DataFrame when pandas is present.
- `display.py` is the single source of truth for parse/format (bytes, perms, tidy, colour).
- Layout is flat: the package is `pyrfs/` at repo root (no `src/`).

## Commands

Workflow is orchestrated by the **Makefile** — `make help` lists everything:

```sh
make gate          # the full gate suite: lint, format-check, typecheck,
                   # test (pandas), test-core, docs build, readme-check
make test          # pytest with the pandas extra
make test-core     # pytest without pandas (prunes the venv first)
make docs-serve    # live-preview the docs site
make readme        # re-render README.md from README.qmd
```

Run **`make gate`** before any commit. Caution: `uv run --extra pandas` leaves pandas in
`.venv`; a plain `uv run pytest` afterwards is NOT a core-mode run — `make test-core`
handles the pruning for you.

## Conventions

- `mypy --strict`, no `Any` in the core package. pandas/numpy are opaque to mypy
  (`follow_imports = "skip"` in pyproject) so results are identical with/without the extra;
  only `pyrfs._pandas.*` has narrow relaxations.
- NumPy-style docstrings on public API; public methods before private in classes.
- fs argument conventions: behavior flags keyword-only; safe defaults
  (`overwrite=False`, `recurse=False` for listing / `True` for `dir_create`, `all=False`,
  `fail=True`); `glob`/`regexp` mutually exclusive → `FsValueError`.
- Errors: native `OSError` subclasses for OS failures; `FsError`/`FsValueError` for
  pyrfs-level validation only.
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
