"""Formatting and parsing helpers — the single source of truth for display.

Everything that turns raw values into human-readable text (or back) lives
here: tidy paths now; byte/permission formatting arrives in P2 and colour
in P6. This module must never import pandas.
"""

from __future__ import annotations

import os
import re

__all__ = ["tidy"]

_MULTI_SLASH = re.compile(r"/{2,}")
_DRIVE_ONLY = re.compile(r"^[A-Za-z]:$")


def tidy(path: str | os.PathLike[str]) -> str:
    """Normalize a path to tidy form: ``/`` separators, no doubled or trailing ``/``.

    Parameters
    ----------
    path : str or os.PathLike
        The path to normalize.

    Returns
    -------
    str
        Tidy path string. ``\\`` becomes ``/``, repeated slashes collapse,
        trailing slashes are stripped (root ``/`` and bare drives like
        ``C:/`` are preserved).

    Examples
    --------
    >>> tidy("src//a.txt/")
    'src/a.txt'
    >>> tidy("C:\\\\data\\\\x")
    'C:/data/x'
    """
    p = os.fspath(path).replace("\\", "/")
    p = _MULTI_SLASH.sub("/", p)
    if len(p) > 1 and p.endswith("/"):
        p = p.rstrip("/") or "/"
    if _DRIVE_ONLY.match(p):
        p += "/"
    return p
