"""Formatting and parsing helpers — the single source of truth for display.

Everything that turns raw values into human-readable text (or back) lives
here: tidy paths, byte sizes, permission strings (colour arrives in P6).
This module must never import pandas.
"""

from __future__ import annotations

import os
import re

from pyfs.errors import FsValueError

__all__ = [
    "humanize_bytes",
    "parse_bytes",
    "parse_perms",
    "perms_to_str",
    "tidy",
]

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


# -- byte sizes ------------------------------------------------------------

_BYTE_UNITS = "BKMGTPEZY"
_PARSE_BYTES = re.compile(
    r"^\s*([0-9]*\.?[0-9]+)\s*([kmgtpezy]?)(?:i?b?)?\s*$",
    re.IGNORECASE,
)


def humanize_bytes(n: int) -> str:
    """Format a byte count for humans, fs-style (base 1024).

    Examples
    --------
    >>> humanize_bytes(455200)
    '444.5K'
    >>> humanize_bytes(10 * 1024**2)
    '10M'
    """
    sign = "-" if n < 0 else ""
    x = abs(int(n))
    if x == 0:
        return "0B"
    exp = min((x.bit_length() - 1) // 10, len(_BYTE_UNITS) - 1)
    if exp == 0:
        return f"{sign}{x}B"
    value = x / 1024**exp
    s = f"{value:.1f}" if value >= 10 else f"{value:.2f}"
    s = s.rstrip("0").rstrip(".")
    return f"{sign}{s}{_BYTE_UNITS[exp]}"


def parse_bytes(value: str) -> int:
    """Parse a human byte-size string into an integer count.

    All units are 1024-based, matching R's fs: ``"10MB"``, ``"10MiB"`` and
    ``"10M"`` all mean ``10 * 1024**2``.

    Raises
    ------
    FsValueError
        If `value` is not a valid size literal.
    """
    m = _PARSE_BYTES.match(value)
    if m is None:
        raise FsValueError(f"invalid byte-size literal: {value!r}")
    num: str = m.group(1)
    unit: str = m.group(2)
    exp = _BYTE_UNITS.index(unit.upper()) if unit else 0
    return round(float(num) * (1 << (10 * exp)))


# -- permissions -----------------------------------------------------------

_OCTAL_PERMS = re.compile(r"^[0-7]{3,4}$")
_RWX_PERMS = re.compile(r"^[rwx-]{9}$")
_SYMBOLIC_CLAUSE = re.compile(r"^([ugoa]*)([+=-])([rwx]*)$")

_WHO_SHIFT = {"u": 6, "g": 3, "o": 0}
_PERM_BIT = {"r": 4, "w": 2, "x": 1}


def perms_to_str(mode: int) -> str:
    """Render the lower 9 permission bits as ``rwxr-xr-x``."""
    out = []
    for shift in (6, 3, 0):
        triad = (mode >> shift) & 0o7
        out.append("r" if triad & 4 else "-")
        out.append("w" if triad & 2 else "-")
        out.append("x" if triad & 1 else "-")
    return "".join(out)


def parse_perms(value: str | int, *, base: int = 0) -> int:
    """Parse permissions from octal (``"644"``), symbolic (``"u+rw,go+r"``),
    display (``"rw-r--r--"``), or raw mode bits.

    Octal, display, and int forms are absolute; symbolic clauses are applied
    on top of `base` (pass the current mode to get chmod semantics).

    Raises
    ------
    FsValueError
        If `value` is not a recognized permission literal.
    """
    if isinstance(value, int):
        return value
    s = value.strip()
    if _OCTAL_PERMS.match(s):
        return int(s, 8)
    if _RWX_PERMS.match(s):
        return _parse_rwx(s)
    return _parse_symbolic(s, base)


def _parse_rwx(s: str) -> int:
    mode = 0
    expected = "rwxrwxrwx"
    for i, ch in enumerate(s):
        if ch == "-":
            continue
        if ch != expected[i]:
            raise FsValueError(f"invalid permission string: {s!r}")
        mode |= 1 << (8 - i)
    return mode


def _parse_symbolic(s: str, base: int = 0) -> int:
    mode = base
    for clause in s.split(","):
        m = _SYMBOLIC_CLAUSE.match(clause.strip())
        if m is None:
            raise FsValueError(f"invalid permission literal: {s!r}")
        who, op, perms = m.groups()
        targets = "ugo" if not who or "a" in who else who
        triad = sum(_PERM_BIT[c] for c in set(perms))
        for w in set(targets):
            shift = _WHO_SHIFT[w]
            if op == "+":
                mode |= triad << shift
            elif op == "-":
                mode &= ~(triad << shift)
            else:
                mode = (mode & ~(0o7 << shift)) | (triad << shift)
    return mode
