# Coming from R's fs

pyrfs keeps fs's **UX contract** — consistent `noun_verb` naming, tidy paths,
predictable typed returns, explicit failure — expressed in idiomatic Python.
If you know fs, your muscle memory transfers: the functional names are identical.

## The four families

| Prefix | Domain | Examples |
|--------|--------|----------|
| `path_` | construct & manipulate path strings (**no I/O**) | `path()`, `path_dir()`, `path_ext_set()`, `path_rel()` |
| `file_` | operate on files | `file_create()`, `file_copy()`, `file_info()`, `file_chmod()` |
| `dir_`  | operate on directories | `dir_create()`, `dir_ls()`, `dir_info()`, `dir_tree()` |
| `link_` | operate on links | `link_create()`, `link_path()`, `link_copy()` |

Plus predicates (`is_file`, `is_dir`, …), `user_ids`/`group_ids`, and temp
helpers (`file_temp`, `path_temp`, `file_temp_push/pop`) — all as in fs.

## Translation table

| R fs | pyrfs functional | pyrfs fluent |
|------|------------------|--------------|
| `path("a", "b", ext = "txt")` | `path("a", "b", ext="txt")` | `FsPath("a") / "b"` then `.with_ext("txt")` |
| `dir_ls("d", recurse = TRUE)` | `dir_ls("d", recurse=True)` | `FsPath("d").ls(recurse=True)` |
| `dir_info("d")` | `dir_info("d")` → DataFrame | — |
| `file_copy("a", "b")` | `file_copy("a", "b")` | `FsPath("a").copy_to("b")` |
| `file_size("a")` | `file_size("a")` → `Bytes` | `FsPath("a").size()` |
| `path_ext_set("a.txt", "md")` | `path_ext_set("a.txt", "md")` | `FsPath("a.txt").with_ext("md")` |
| `path_rel("a/b", "a")` | `path_rel("a/b", "a")` | `FsPath("a/b").rel_to("a")` |
| `dir_tree("d")` | `dir_tree("d")` | `FsPath("d").tree()` |
| `fs_bytes("10MB")` | `Bytes("10MB")` | — |
| `fs_perms("644")` | `Perms("644")` | — |
| `x %>% file_delete()` | loop / `df.pipe(...)` | `FsPath(x).delete()` |

## The headline demo, ported

```r
# R
dir_info("src", recurse = FALSE) |>
  filter(type == "file", size > "10KB") |>
  arrange(desc(size))
```

```python
# Python (with the pandas extra)
(fs.dir_info("src")
   .query("size > '10KB' and type == 'file'")
   .sort_values("size", ascending=False))
```

`size` and `permissions` are real pandas ExtensionDtypes, so comparisons
against human literals work inside `.query()` — same trick as fs's
`fs_bytes`/`fs_perms` tibble columns.

## Vectorization

fs is vectorized end to end; Python is scalar-by-default. pyrfs functions are
**polymorphic on the first argument**:

```python
fs.path_ext("a.txt")              # 'txt'                 (scalar -> scalar)
fs.path_ext(["a.txt", "b.md"])    # ['txt', 'md']         (list -> list)
fs.path_ext(df["path"])           # pandas Series          (Series -> Series)
df["path"].fs.ext()               # the idiomatic column form
```

## What's different (on purpose)

- **Errors are Python-native.** `FileExistsError`/`FileNotFoundError`/
  `PermissionError` instead of classed `fs_error` conditions; `FsValueError`
  for pyrfs-level validation. `tryCatch` → `try/except`.
- **`recurse` defaults match fs** (`False` for listing, `True` for
  `dir_create`), and accepts an `int` depth, exactly like fs.
- **Byte units are 1024-based across the board** — `Bytes("10MB") ==
  Bytes("10MiB")`, matching `fs_bytes`.
- **`is_file`/`is_dir` classify the entry itself** (lstat): a symlink answers
  `True` only to `is_link` — fs semantics, not `os.path.isdir` semantics.
- **No `dir_move()`** — directories move via `file_move()`, same as fs.
- **`FsPath` is a `str`, not a `pathlib.Path`.** Best interop and pandas
  round-tripping; call `.as_pathlib()` when you want pathlib semantics. The
  `/` join concatenates then tidies — an absolute right-hand side does *not*
  reset the path (unlike `os.path.join`).
- **The split method is `parts()`** — `str.split()` is left untouched so
  `FsPath` never surprises code that treats it as a string.
- **`dir_walk()` is a lazy generator** rather than a callback walker — the
  Pythonic spin; `dir_ls()`/`dir_map()` are built on it.
