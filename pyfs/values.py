"""Typed scalar values — sizes and permissions that *know what they are*.

``Bytes`` subclasses ``int`` and ``Perms`` subclasses ``int``, mirroring
fs's S3-over-atomic-vector design (``fs_bytes ⊂ numeric``,
``fs_perms ⊂ integer``): the value still behaves like its base type
everywhere, but parses human literals and prints for humans.
"""

from __future__ import annotations

from pyfs.display import humanize_bytes, parse_bytes, parse_perms, perms_to_str

__all__ = ["Bytes", "Perms"]


class Bytes(int):
    """A byte count that parses and displays human-readable sizes.

    All units are 1024-based (``"10MB"`` == ``"10MiB"`` == ``10 * 1024**2``),
    matching R's fs.

    Examples
    --------
    >>> Bytes("10MB")
    Bytes(10485760)
    >>> str(Bytes(455200))
    '444.5K'
    >>> Bytes(455200) < "1MB"
    True
    >>> str(Bytes("1MB") + "500KB")
    '1.49M'
    """

    __slots__ = ()

    def __new__(cls, value: int | float | str = 0) -> Bytes:
        if isinstance(value, str):
            return super().__new__(cls, parse_bytes(value))
        return super().__new__(cls, round(value))

    def __str__(self) -> str:
        return humanize_bytes(self)

    def __repr__(self) -> str:
        return f"Bytes({int(self)})"

    def __format__(self, format_spec: str) -> str:
        if not format_spec:
            return humanize_bytes(self)
        return int.__format__(self, format_spec)

    # -- comparisons accept human literals on the right --------------------
    def __eq__(self, other: object) -> bool:
        coerced = _size_operand(other)
        if coerced is None:
            return NotImplemented
        return int(self) == coerced

    def __ne__(self, other: object) -> bool:
        coerced = _size_operand(other)
        if coerced is None:
            return NotImplemented
        return int(self) != coerced

    __hash__ = int.__hash__

    def __lt__(self, other: int | float | str) -> bool:
        return float(self) < _size_number(other)

    def __le__(self, other: int | float | str) -> bool:
        return float(self) <= _size_number(other)

    def __gt__(self, other: int | float | str) -> bool:
        return float(self) > _size_number(other)

    def __ge__(self, other: int | float | str) -> bool:
        return float(self) >= _size_number(other)

    # -- arithmetic stays Bytes ---------------------------------------------
    def __add__(self, other: int | str) -> Bytes:
        return Bytes(int(self) + _size_int(other))

    def __radd__(self, other: int | str) -> Bytes:
        return Bytes(_size_int(other) + int(self))

    def __sub__(self, other: int | str) -> Bytes:
        return Bytes(int(self) - _size_int(other))

    def __rsub__(self, other: int | str) -> Bytes:
        return Bytes(_size_int(other) - int(self))

    def __mul__(self, other: int) -> Bytes:
        return Bytes(int(self) * other)

    def __rmul__(self, other: int) -> Bytes:
        return Bytes(other * int(self))

    def __floordiv__(self, other: int | str) -> Bytes:
        return Bytes(int(self) // _size_int(other))

    def __truediv__(self, other: int | float | str) -> float:
        return float(self) / _size_number(other)

    def __neg__(self) -> Bytes:
        return Bytes(-int(self))

    def __abs__(self) -> Bytes:
        return Bytes(abs(int(self)))


class Perms(int):
    """Unix permission bits that parse and display ``rwxr-xr-x`` style.

    Construct from octal (``"644"``), symbolic (``"u+rw,go+r"``), display
    (``"rw-r--r--"``) strings, or raw mode bits.

    Examples
    --------
    >>> Perms("644")
    Perms('rw-r--r--')
    >>> Perms("644") == "rw-r--r--"
    True
    >>> str(Perms("644") | "u+x")
    'rwxr--r--'
    """

    __slots__ = ()

    def __new__(cls, value: int | str = 0) -> Perms:
        return super().__new__(cls, parse_perms(value) & 0o7777)

    def __str__(self) -> str:
        return perms_to_str(self)

    def __repr__(self) -> str:
        return f"Perms('{perms_to_str(self)}')"

    def __format__(self, format_spec: str) -> str:
        if not format_spec:
            return perms_to_str(self)
        return int.__format__(self, format_spec)

    # -- mode algebra stays Perms; strings parse on the right ---------------
    def __eq__(self, other: object) -> bool:
        coerced = _perm_operand(other)
        if coerced is None:
            return NotImplemented
        return int(self) == coerced

    def __ne__(self, other: object) -> bool:
        coerced = _perm_operand(other)
        if coerced is None:
            return NotImplemented
        return int(self) != coerced

    __hash__ = int.__hash__

    def __and__(self, other: int | str) -> Perms:
        return Perms(int(self) & parse_perms(other))

    def __rand__(self, other: int | str) -> Perms:
        return Perms(parse_perms(other) & int(self))

    def __or__(self, other: int | str) -> Perms:
        return Perms(int(self) | parse_perms(other))

    def __ror__(self, other: int | str) -> Perms:
        return Perms(parse_perms(other) | int(self))

    def __xor__(self, other: int | str) -> Perms:
        return Perms(int(self) ^ parse_perms(other))

    def __rxor__(self, other: int | str) -> Perms:
        return Perms(parse_perms(other) ^ int(self))

    def __invert__(self) -> Perms:
        return Perms(~int(self) & 0o777)


def _size_int(value: int | str) -> int:
    return parse_bytes(value) if isinstance(value, str) else value


def _size_number(value: int | float | str) -> float:
    return float(parse_bytes(value)) if isinstance(value, str) else float(value)


def _size_operand(value: object) -> int | float | None:
    """Coerce an equality operand to a number, or None if incomparable."""
    if isinstance(value, str):
        try:
            return parse_bytes(value)
        except Exception:
            return None
    if isinstance(value, (int, float)):
        return value
    return None


def _perm_operand(value: object) -> int | None:
    """Coerce an equality operand to mode bits, or None if incomparable."""
    if isinstance(value, str):
        try:
            return parse_perms(value)
        except Exception:
            return None
    if isinstance(value, int):
        return value
    return None
