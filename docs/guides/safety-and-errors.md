# Safety & errors

pyrfs inherits fs's stance: **explicit failure, destructive actions opt-in**.
Nothing silently returns `False`; nothing clobbers unless you ask.

## Safe defaults (learn once)

| Argument | Meaning | Default | On |
|----------|---------|---------|-----|
| `overwrite` | allow clobbering an existing target | `False` | copy/move |
| `recurse` | `True` = fully, `False` = no, `int` = to depth | `False` listing / `True` create | `dir_*` |
| `all` | include hidden dotfiles | `False` | `dir_ls`, `dir_map`, … |
| `type` | filter by entry type (`"file"`, `"directory"`, …) | `"any"` | traversals |
| `glob` / `regexp` | filter listings (mutually exclusive) | `None` | `dir_ls`, `path_filter` |
| `fail` | raise vs warn on unreadable entries | `True` | traversals |

Behavior flags are keyword-only, so call sites read self-documenting:
`file_copy(a, b, overwrite=True)`.

## The error model

```python
fs.file_copy("a.txt", "b.txt")        # FileExistsError if b.txt exists
fs.dir_ls("nope")                     # FileNotFoundError
fs.path_filter(ps, glob="*.py", regexp=r"\.py$")
                                      # FsValueError: cannot set both
```

- **OS-level failures raise native `OSError` subclasses** —
  `FileNotFoundError`, `FileExistsError`, `PermissionError` — familiar and
  `except`-able.
- **pyrfs-level validation raises `FsError`** (usually the `FsValueError`
  subclass): conflicting arguments, bad size/permission literals, deleting a
  non-symlink with `link_delete`.

## Softening traversals: `fail=False`

One unreadable entry shouldn't abort a whole directory walk:

```python
fs.dir_ls("/var", recurse=True, fail=False)
# UserWarning: skipping unreadable directory: ...
# -> returns everything it *could* read
```

This is a direct port of fs's `fail` knob, and applies to `dir_ls`,
`dir_walk`, `dir_map`, and `dir_info`.

## Destination resolution (copy/move)

Copying or moving **into an existing directory** targets `dir/basename` —
shell `cp`/`mv` semantics — and the `overwrite` guard applies to that
*resolved* target:

```python
fs.file_copy("report.pdf", "archive/")     # -> FsPath('archive/report.pdf')
fs.file_copy("report.pdf", "archive/")     # FileExistsError
```

There is no `dir_move()`: directories are files at the OS level, so
`file_move()` moves them — same deliberate choice as fs.
