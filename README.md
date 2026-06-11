# pyrfs

[![CI](https://github.com/Lightbridge-KS/pyrfs/actions/workflows/ci.yml/badge.svg)](https://github.com/Lightbridge-KS/pyrfs/actions/workflows/ci.yml)
[![Python ≥ 3.10](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://github.com/Lightbridge-KS/pyrfs)

**Pythonic filesystem ergonomics, inspired by R's [fs](https://fs.r-lib.org).**
Tidy paths, typed self-describing values, explicit failure — chainable, and
pandas-native. Pure Python, zero hard dependencies.

📖 **Docs: <https://pyrfs.netlify.app>** · [Coming from R's fs](https://pyrfs.netlify.app/coming-from-r/) · [API reference](https://pyrfs.netlify.app/api/paths/)

```python
import pyrfs as fs
from pyrfs import FsPath

# functional — R fs names transfer directly
fs.dir_ls("src", recurse=True, glob="*.py")     # [FsPath('src/app.py'), ...]
fs.file_size("data.csv") > "10MB"               # sizes compare to literals
fs.file_copy("a.txt", "backup/")                # refuses to clobber by default

# fluent — FsPath is a str, so it drops in anywhere
(FsPath("data") / "raw.csv").with_ext("parquet").copy_to("clean/")

# pandas — typed columns, string literals work in .query()
(fs.dir_info("src", recurse=True)
   .query("size > '10KB' and type == 'file'")
   .sort_values("size", ascending=False))
```

## Install

Pre-release — not yet on PyPI:

```sh
pip install "pyrfs @ git+https://github.com/Lightbridge-KS/pyrfs"
# with the pandas integration:
pip install "pyrfs[pandas] @ git+https://github.com/Lightbridge-KS/pyrfs"
```

## Features

- **Consistent `noun_verb` API** in four families — `path_*` (pure string
  algebra), `file_*`, `dir_*`, `link_*` — plus predicates and temp helpers.
- **Three interchangeable surfaces**: functional, fluent `FsPath` chaining,
  and a pandas `.fs` Series accessor — one engine underneath.
- **Typed values that print for humans**: `Bytes(455200)` displays `444.5K`
  and compares against `"1MB"`; `Perms("644")` displays `rw-r--r--`.
- **Safe by default**: `overwrite=False`, bounded recursion, explicit
  exceptions — nothing silently returns `False`, nothing clobbers unasked.
- **pandas-native**: `dir_info()` returns a DataFrame with real
  `bytes`/`perms`/`path` ExtensionDtypes; without pandas, the core works
  unchanged.
- Pure Python ≥ 3.10, zero hard dependencies, fully typed (`mypy --strict`),
  tested on Python 3.10–3.13.

Coming from R? Start with
**[Coming from R's fs](https://pyrfs.netlify.app/coming-from-r/)**. The
[design docs](https://pyrfs.netlify.app/design/pyrfs-ux/) describe the UX
contract and architecture. The docs site also serves
[llms.txt](https://pyrfs.netlify.app/llms.txt) /
[llms-full.txt](https://pyrfs.netlify.app/llms-full.txt) for AI agents.

## License

MIT
