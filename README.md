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

## Status

Core (paths, files, dirs, links, typed values, pandas layer) is implemented and
tested on Python 3.10–3.13. See the
[progress tracker](https://pyrfs.netlify.app/design/PROGRESS/) and
[design docs](https://pyrfs.netlify.app/design/pyrfs-ux/).

## License

MIT
