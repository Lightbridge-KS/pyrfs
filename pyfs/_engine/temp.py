"""Temp-path helpers: ``file_temp`` and its deterministic push/pop stack.

``file_temp()`` returns a fresh temp *name* (it does not create the file).
``file_temp_push()`` queues deterministic names that subsequent
``file_temp()`` calls return first — the fs trick for reproducible
examples, docs, and tests.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Iterable

from pyfs._engine.vectorize import PathInput
from pyfs.fspath import FsPath

__all__ = ["file_temp", "file_temp_pop", "file_temp_push"]

_TEMP_STACK: list[FsPath] = []


def file_temp(
    pattern: str = "file",
    tmp_dir: PathInput | None = None,
    ext: str = "",
) -> FsPath:
    """Return a unique temp path (name only — the file is not created).

    If names were queued with :func:`file_temp_push`, the oldest queued
    name is returned instead (deterministic mode).

    Examples
    --------
    >>> file_temp(ext="csv")  # doctest: +SKIP
    FsPath('/tmp/file2bf36b4eb5d8.csv')
    """
    if _TEMP_STACK:
        return _TEMP_STACK.pop(0)
    base = FsPath(tmp_dir) if tmp_dir is not None else FsPath(tempfile.gettempdir())
    suffix = f".{ext.lstrip('.')}" if ext else ""
    return base / f"{pattern}{uuid.uuid4().hex[:12]}{suffix}"


def file_temp_push(path: PathInput | Iterable[PathInput]) -> list[FsPath]:
    """Queue deterministic path(s) for subsequent :func:`file_temp` calls."""
    if isinstance(path, (str, os.PathLike)):
        items: list[FsPath] = [FsPath(path)]
    else:
        items = [FsPath(p) for p in path]
    _TEMP_STACK.extend(items)
    return items


def file_temp_pop() -> FsPath | None:
    """Remove and return the oldest queued temp path (``None`` if empty)."""
    if _TEMP_STACK:
        return _TEMP_STACK.pop(0)
    return None
