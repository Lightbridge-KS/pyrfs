# The three surfaces

Every pyrfs operation is implemented **once** in a pure-stdlib engine; the three
user-facing surfaces are thin delegates. They interoperate freely — `dir_ls()`
returns `FsPath`s you can chain methods on or drop into a DataFrame column.

## A — Functional: scripts and R muscle memory

```python
import pyrfs as fs

files = fs.dir_ls("data", recurse=True, glob="*.csv")
fs.dir_create("backup")
for f in files:
    fs.file_copy(f, "backup/", overwrite=True)
```

Names mirror R's fs exactly — see [Coming from R's fs](../coming-from-r.md).
Functions are polymorphic on the first argument (scalar → scalar, list → list,
Series → Series).

## B — Fluent `FsPath`: OO-style chaining

```python
from pyrfs import FsPath

report = (FsPath("analysis") / "draft.md").with_ext("html")
work = FsPath("project").mkdir().touch_file("README.md").touch_file("setup.py")
big_logs = [p for p in FsPath("logs").walk(glob="*.log") if p.size() > "5MB"]
```

Because `FsPath` subclasses `str`:

- `open(p)`, `pd.read_csv(p)`, `json.dump(..., open(p, "w"))` all just work;
- every `str` method behaves normally (`p.startswith("src/")`, `p.split("/")`);
- it serializes cleanly (JSON, parquet, databases) as a plain string.

Mutating verbs return the resulting path, so chains read top-to-bottom like
R pipes.

## C — pandas: columns and frames

Requires the extra: `pip install "pyrfs[pandas]"`.

```python
import pandas as pd
import pyrfs as fs

# typed frame in, typed frame out
big = (fs.dir_info("src", recurse=True)
         .query("size > '10KB' and type == 'file'")
         .sort_values("size", ascending=False))

# vectorized path algebra over a column
df = pd.DataFrame({"path": fs.dir_ls("src", recurse=True, type="file")})
df.assign(
    ext=df["path"].fs.ext(),
    dir=df["path"].fs.dir(),
    size=df["path"].fs.size(),     # a real 'bytes'-dtype column
)
```

Without pandas installed, the core works unchanged and `*_info` returns
`list[dict]` rows carrying the same typed scalars.

## Choosing

| Situation | Reach for |
|-----------|-----------|
| Shell-script-like automation, R habits | **A** functional |
| Building paths through transformations, OO code | **B** fluent |
| Filtering/aggregating many files as data | **C** pandas |
