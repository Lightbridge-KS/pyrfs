# pyrfs


<!-- README.md is generated from README.qmd: edit that file, then render with
     `uv run --group docs --extra pandas quarto render README.qmd` -->

[![CI](https://github.com/Lightbridge-KS/pyrfs/actions/workflows/ci.yml/badge.svg)](https://github.com/Lightbridge-KS/pyrfs/actions/workflows/ci.yml)
[![Python ≥
3.10](https://img.shields.io/badge/python-%E2%89%A53.10-blue.svg)](https://github.com/Lightbridge-KS/pyrfs)
[![docs](https://img.shields.io/badge/docs-pyrfs.netlify.app-teal.svg)](https://pyrfs.netlify.app)
[![status](https://img.shields.io/badge/lifecycle-alpha-orange.svg)](https://pyrfs.netlify.app)

**pyrfs** provides a uniform, chainable interface to file system
operations, porting the UX of R’s [fs](https://fs.r-lib.org) package to
Python. It is **pure Python over the standard library** — no compiled
extension, no dependencies — adding the ergonomics the stdlib leaves
out: one consistent namespace, tidy paths, typed self-describing values,
and explicit failure.

📖 **Documentation: <https://pyrfs.netlify.app>**

## Installation

Pre-release — install from GitHub:

``` sh
pip install "pyrfs @ git+https://github.com/Lightbridge-KS/pyrfs"
# with the pandas integration:
pip install "pyrfs[pandas] @ git+https://github.com/Lightbridge-KS/pyrfs"
```

## Comparison vs the standard library

Python’s file APIs accreted across `os`, `os.path`, `shutil`, `glob`,
`pathlib`, and `tempfile`. **pyrfs** smooths over the seams:

- **One namespace, predictable names.** Functions are grouped by the
  noun they act on — `path_*` (pure string algebra), `file_*`, `dir_*`,
  `link_*` — so `dir_` + <kbd>Tab</kbd> shows every directory operation.
  No more remembering that creating is `os.makedirs` but removing is
  `shutil.rmtree`.

- **Predictable, path-carrying returns.** Mutating verbs return the new
  path (so calls chain); queries return typed values. Compare
  `os.path.getsize()` → bare `int` vs `file_size()` → `Bytes` that
  displays `444.5K` and compares against `"10KB"`.

- **Explicit failure, safe defaults.** `shutil.copy2()` silently
  overwrites its target; `file_copy()` raises `FileExistsError` unless
  you pass `overwrite=True`. Traversals raise on unreadable entries
  unless you soften them with `fail=False`.

- **Polymorphic over scalars, lists, and pandas Series.** Every path
  function accepts one path or many — vectorization like fs, the
  Pythonic way.

- **Tidy paths.** Always `/` separators, never doubled or trailing — and
  in a terminal, paths are coloured by file type via `LS_COLORS`
  (degrading automatically on non-TTY or `NO_COLOR`).

## Usage

pyrfs functions are divided into four main families:

- `path_` for manipulating and constructing paths
- `file_` for files
- `dir_` for directories
- `link_` for links

Directories and links are special types of files, so `file_` functions
generally also work on them (there is deliberately no `dir_move()` — use
`file_move()`).

``` python
import pyrfs as fs

# construct a path with path()
fs.path("foo", "bar", "a", ext="txt")
```

    FsPath('foo/bar/a.txt')

``` python
# list files
fs.dir_ls("pyrfs", glob="*.py")
```

    [FsPath('pyrfs/__init__.py'),
     FsPath('pyrfs/display.py'),
     FsPath('pyrfs/errors.py'),
     FsPath('pyrfs/fspath.py'),
     FsPath('pyrfs/info.py'),
     FsPath('pyrfs/values.py')]

``` python
# create a new directory
tmp = fs.dir_create(fs.file_temp())
tmp
```

    FsPath('/tmp/pyrfs-demo/data')

``` python
# create new files in that directory
fs.file_create(tmp / "my-file.txt")
fs.dir_ls(tmp)
```

    [FsPath('/tmp/pyrfs-demo/data/my-file.txt')]

``` python
# remove files from the directory
fs.file_delete(tmp / "my-file.txt")
fs.dir_ls(tmp)
```

    []

``` python
# remove the directory
fs.dir_delete(tmp);
```

### Chaining — the Pythonic pipe

Where R pipes
`file_temp() |> dir_create() |> path(letters[1:3]) |> file_create()`,
pyrfs chains: every mutating verb returns the resulting `FsPath` (which
**is** a `str`, so it drops into `open()`, `pd.read_csv()`, or any API
expecting a path).

``` python
from pyrfs import FsPath

(FsPath(fs.file_temp())
    .mkdir()
    .touch_file("a").touch_file("b").touch_file("c")
    .ls())
```

    [FsPath('/tmp/pyrfs-demo/chain/a'),
     FsPath('/tmp/pyrfs-demo/chain/b'),
     FsPath('/tmp/pyrfs-demo/chain/c')]

## pyrfs + pandas

With the `[pandas]` extra, `dir_info()` returns a DataFrame whose
`path`, `size`, and `permissions` columns are real ExtensionDtypes — so
string literals work inside `.query()`, exactly like fs’s typed tibble
columns:

``` python
import pandas as pd

big = (fs.dir_info("pyrfs", recurse=True, glob="*.py")
         .query("size > '4KB' and type == 'file'")
         .sort_values("size", ascending=False)
         .loc[:, ["path", "permissions", "size"]])
print(big.to_string(index=False))
```

                        path permissions  size
     pyrfs/_engine/dirops.py   rw-r--r--  9.2K
             pyrfs/fspath.py   rw-r--r-- 8.09K
      pyrfs/_engine/paths.py   rw-r--r-- 8.04K
    pyrfs/_engine/fileops.py   rw-r--r-- 7.53K
     pyrfs/_pandas/arrays.py   rw-r--r-- 7.26K
            pyrfs/display.py   rw-r--r-- 7.22K
             pyrfs/values.py   rw-r--r-- 6.11K

The `.fs` accessor vectorizes path operations over a Series:

``` python
paths = pd.Series(fs.dir_ls("pyrfs/_engine", glob="*ops.py"))
print(paths.fs.size())
```

    0     9.2K
    1    7.53K
    2    2.03K
    dtype: bytes

And reading a collection of files into one frame — the
`purrr::map_df(.id=)` trick — is a dict comprehension away, because
`dir_ls()` returns paths whose `.name()` you can key on:

``` python
tsv_dir = fs.dir_create(fs.file_temp())
df = pd.DataFrame({"species": ["adelie", "adelie", "gentoo"], "mass": [3800, 3250, 5000]})
for species, d in df.groupby("species"):
    d.to_csv(tsv_dir / f"{species}.tsv", sep="\t", index=False)

files = fs.dir_ls(tsv_dir, glob="*.tsv")
combined = pd.concat({f.name(): pd.read_csv(f, sep="\t") for f in files}, names=["file"])
print(combined)
```

                 species  mass
    file                      
    adelie.tsv 0  adelie  3800
               1  adelie  3250
    gentoo.tsv 0  gentoo  5000

## Coming from R’s fs?

The functional names are identical, so muscle memory transfers:

| R fs | pyrfs |
|----|----|
| `dir_ls("d", recurse = TRUE)` | `dir_ls("d", recurse=True)` |
| `file_copy("a", "b")` | `file_copy("a", "b")` or `FsPath("a").copy_to("b")` |
| `dir_info("d") \|> filter(size > "10KB")` | `dir_info("d").query("size > '10KB'")` |

See the full **[translation
guide](https://pyrfs.netlify.app/coming-from-r/)** and the honest list
of deliberate differences.

## Documentation & feedback

The **[docs site](https://pyrfs.netlify.app)** has guides, an executable
tour notebook, and the API reference — plus
[llms.txt](https://pyrfs.netlify.app/llms.txt) /
[llms-full.txt](https://pyrfs.netlify.app/llms-full.txt) for AI agents.
Bug reports and feature requests: [GitHub
issues](https://github.com/Lightbridge-KS/pyrfs/issues).

## License

MIT
