# Typed values

The heart of fs's charm: values that *know what they are* and print for humans.
pyrfs ships three — each subclasses a builtin, so it still behaves like its base
type everywhere.

## `Bytes` ⊂ `int`

```python
from pyrfs import Bytes

Bytes("10MB")                        # Bytes(10485760)
str(Bytes(455200))                   # '444.5K'
Bytes(455200) < "1MB"                # True — comparisons parse literals
sum([Bytes("1MB"), Bytes("500KB")])  # Bytes -> '1.49M' (arithmetic stays typed)
```

!!! note "All units are 1024-based"
    `"10MB"`, `"10MiB"` and `"10M"` all mean `10 * 1024**2`, matching R's
    `fs_bytes`. `repr()` stays exact (`Bytes(455200)`); `str()`/`format()`
    humanize.

`file_size()` returns `Bytes`, so `fs.file_size("x.bin") > "10KB"` reads like
the question you're asking.

## `Perms` ⊂ `int`

```python
from pyrfs import Perms

Perms("644")                  # Perms('rw-r--r--')
Perms("644") == "rw-r--r--"   # True
Perms("644") == "u=rw,go=r"   # True — symbolic forms parse too
Perms("644") | "u+x"          # Perms('rwxr--r--') — mode algebra stays typed
```

`file_chmod()` accepts all the same forms, and symbolic modes apply **relative
to the current mode** (chmod semantics): `fs.file_chmod("run.sh", "u+x")`.

## `FsPath` ⊂ `str`

```python
from pyrfs import FsPath

FsPath("src//a.txt/")         # FsPath('src/a.txt')  — tidied on construction
FsPath("a") / "b" / "c.md"    # FsPath('a/b/c.md')
```

Tidy form: always `/` separators, no doubled or trailing slashes. In a
terminal, the repr is coloured by on-disk type via `LS_COLORS` (degrades
automatically on non-TTY or `NO_COLOR`).

## In pandas columns

With the `[pandas]` extra these become real ExtensionDtypes — `"bytes"`,
`"perms"`, `"path"` — so whole columns display humanized, sort correctly,
compare against literals inside `.query()`, and `sum()`/`min()`/`max()` return
typed scalars:

```python
s = pd.Series(["1K", "10MB", "455"], dtype="bytes")
s > "1K"          # [False, True, False]
s.sum()           # Bytes -> '10M'
```
