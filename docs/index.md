# pyrfs

**Pythonic filesystem ergonomics, inspired by R's [fs](https://fs.r-lib.org).**

Tidy paths, typed self-describing values, explicit failure — chainable, and
pandas-native. Pure Python ≥ 3.10, zero hard dependencies.

```python
import pyrfs as fs

fs.dir_ls("src", recurse=True, glob="*.py")   # [FsPath('src/app.py'), ...]
fs.file_size("data.csv") > "10MB"             # True — sizes compare to literals
fs.file_copy("a.txt", "backup/")              # FsPath('backup/a.txt'), refuses to clobber
```

## Install

Not yet on PyPI — install from GitHub:

```sh
pip install "pyrfs @ git+https://github.com/Lightbridge-KS/pyrfs"
# with the pandas integration:
pip install "pyrfs[pandas] @ git+https://github.com/Lightbridge-KS/pyrfs"
```

## One engine, three surfaces

Every operation is implemented once and reachable three ways — pick per task,
mix freely:

=== "A — Functional"

    ```python
    import pyrfs as fs

    fs.path("foo", "bar", "a", ext="txt")    # FsPath('foo/bar/a.txt')
    fs.dir_ls("data", glob="*.csv")
    fs.file_copy("a.txt", "b.txt")           # -> FsPath('b.txt')
    ```

    Closest to R's fs — the `noun_verb` names transfer directly.
    See [Coming from R's fs](coming-from-r.md).

=== "B — Fluent FsPath"

    ```python
    from pyrfs import FsPath

    (FsPath("data") / "raw.csv").with_ext("parquet").copy_to("clean/")
    FsPath("project").mkdir().touch_file("README.md")
    FsPath("logs").ls(glob="*.log")
    ```

    `FsPath` **is a `str`** — it drops into `open()`, `pd.read_csv()`,
    any API that takes a path.

=== "C — pandas"

    ```python
    import pyrfs as fs

    (fs.dir_info("src", recurse=True)
       .query("size > '10KB' and type == 'file'")   # typed columns!
       .sort_values("size", ascending=False))

    df["path"].fs.ext()        # vectorized over a column
    ```

    `size` and `permissions` are real ExtensionDtypes — string literals work
    inside `.query()`.

## Where next

- **[Coming from R's fs](coming-from-r.md)** — the translation table.
- **[The three surfaces](guides/three-surfaces.md)** — when to use which.
- **[Typed values](guides/typed-values.md)** — `Bytes('444.5K')`, `Perms('rw-r--r--')`.
- **[Tour notebook](tour/pyrfs-tour.ipynb)** — everything, runnable.
- **[API reference](api/paths.md)** — by family: `path_*`, `file_*`, `dir_*`, `link_*`.
