"""ExtensionArrays backing the pyfs column dtypes.

One small base class implements the pandas protocol; the three concrete
arrays only define how to parse and box scalars. Operators come from
``ExtensionScalarOpsMixin``, which lifts the *scalar* semantics elementwise —
so ``size_column > "10KB"`` works because ``Bytes > "10KB"`` works. No
formatting or parsing logic lives here; it is all in ``display.py`` via the
scalar types.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import ClassVar

import numpy as np
import pandas as pd
from pandas.api.extensions import (
    ExtensionArray,
    ExtensionDtype,
    ExtensionScalarOpsMixin,
)
from pandas.api.extensions import take as pd_take

from pyfs._pandas.dtypes import BytesDtype, PathDtype, PermsDtype
from pyfs.display import parse_bytes, parse_perms
from pyfs.fspath import FsPath
from pyfs.values import Bytes, Perms

__all__ = ["BytesArray", "PathArray", "PermsArray"]


class _FsArray(ExtensionArray, ExtensionScalarOpsMixin):
    """Shared pandas-protocol plumbing over a 1-D numpy backing array."""

    _np_dtype: ClassVar[str] = "float64"

    def __init__(self, values: object, copy: bool = False) -> None:
        data = np.asarray(values, dtype=self._np_dtype)
        self._data = data.copy() if copy else data

    # -- construction -------------------------------------------------------
    @classmethod
    def _from_sequence(
        cls, scalars: Sequence[object], *, dtype: object = None, copy: bool = False
    ) -> _FsArray:
        return cls([cls._parse_scalar(s) for s in scalars])

    @classmethod
    def _from_factorized(cls, values: object, original: _FsArray) -> _FsArray:
        return cls(values)

    @classmethod
    def _concat_same_type(cls, to_concat: Sequence[_FsArray]) -> _FsArray:
        return cls(np.concatenate([arr._data for arr in to_concat]))

    # -- basic protocol ------------------------------------------------------
    def __getitem__(self, item: object) -> object:
        if isinstance(item, (int, np.integer)):
            return self._box_scalar(self._data[item])
        return type(self)(self._data[item])

    def __len__(self) -> int:
        return len(self._data)

    def __array__(self, dtype: object = None, copy: object = None) -> np.ndarray:
        if dtype is None or np.dtype(dtype) == object:
            # boxed scalars, so repr/formatting shows '444.5K' / 'rw-r--r--'
            return np.asarray([self._box_scalar(v) for v in self._data], dtype=object)
        return np.asarray(self._data, dtype=dtype)

    @property
    def nbytes(self) -> int:
        return int(self._data.nbytes)

    def isna(self) -> np.ndarray:
        return np.asarray(pd.isna(self._data))

    def copy(self) -> _FsArray:
        return type(self)(self._data.copy())

    def take(
        self, indices: object, *, allow_fill: bool = False, fill_value: object = None
    ) -> _FsArray:
        if allow_fill and fill_value is None:
            fill_value = self.dtype.na_value
        data = pd_take(self._data, indices, allow_fill=allow_fill, fill_value=fill_value)
        return type(self)(data)

    def _values_for_argsort(self) -> np.ndarray:
        return self._data

    def _formatter(self, boxed: bool = False) -> Callable[[object], str]:
        return str

    # -- hooks for the concrete arrays ---------------------------------------
    @classmethod
    def _parse_scalar(cls, value: object) -> object:
        raise NotImplementedError

    def _box_scalar(self, value: object) -> object:
        raise NotImplementedError


class BytesArray(_FsArray):
    """Byte sizes; float64-backed (like fs's numeric ``fs_bytes``), NaN = NA."""

    @property
    def dtype(self) -> ExtensionDtype:
        return BytesDtype()

    @classmethod
    def _parse_scalar(cls, value: object) -> float:
        if value is None or value is pd.NA:
            return float("nan")
        if isinstance(value, str):
            return float(parse_bytes(value))
        if isinstance(value, (int, float)):  # incl. Bytes; NaN passes through
            return float(value)
        return float(value)  # type: ignore[arg-type]  # numpy scalars

    def _box_scalar(self, value: object) -> object:
        if pd.isna(value) or not isinstance(value, float):  # backing is float64
            return self.dtype.na_value
        return Bytes(value)

    def _reduce(
        self, name: str, *, skipna: bool = True, keepdims: bool = False, **kwargs: object
    ) -> object:
        result = _numeric_reduce(self._data, name, skipna, self.dtype)
        boxed = Bytes(result) if name in ("sum", "min", "max") else result
        if keepdims:
            return type(self)([float(result)])
        return boxed


class PermsArray(_FsArray):
    """Permission bits; displays ``rwxr-xr-x``, compares against literals."""

    @property
    def dtype(self) -> ExtensionDtype:
        return PermsDtype()

    @classmethod
    def _parse_scalar(cls, value: object) -> float:
        if value is None or value is pd.NA:
            return float("nan")
        if isinstance(value, str):
            return float(parse_perms(value))
        if isinstance(value, (int, float)):
            return float(value)
        return float(value)  # type: ignore[arg-type]  # numpy scalars

    def _box_scalar(self, value: object) -> object:
        if pd.isna(value) or not isinstance(value, float):  # backing is float64
            return self.dtype.na_value
        return Perms(int(value))

    def _reduce(
        self, name: str, *, skipna: bool = True, keepdims: bool = False, **kwargs: object
    ) -> object:
        if name not in ("min", "max"):
            raise TypeError(f"cannot perform {name!r} on a perms column")
        result = _numeric_reduce(self._data, name, skipna, self.dtype)
        if keepdims:
            return type(self)([float(result)])
        return Perms(int(result))


class PathArray(_FsArray):
    """Tidy ``FsPath`` values; object-backed."""

    _np_dtype = "object"

    @property
    def dtype(self) -> ExtensionDtype:
        return PathDtype()

    @classmethod
    def _parse_scalar(cls, value: object) -> object:
        if value is None or (isinstance(value, float) and np.isnan(value)) or value is pd.NA:
            return None
        if isinstance(value, (str, os.PathLike)):
            return FsPath(value)
        return FsPath(str(value))

    def _box_scalar(self, value: object) -> object:
        return value

    def _values_for_argsort(self) -> np.ndarray:
        return np.asarray(["" if v is None else str(v) for v in self._data], dtype=object)


def _numeric_reduce(data: np.ndarray, name: str, skipna: bool, dtype: object) -> float:
    values = data[~np.isnan(data)] if skipna else data
    if name == "sum":
        return float(np.sum(values)) if len(values) else 0.0
    if name == "min":
        return float(np.min(values))
    if name == "max":
        return float(np.max(values))
    if name == "mean":
        return float(np.mean(values))
    raise TypeError(f"cannot perform {name!r} on a {dtype} column")


# Lift the scalar operator semantics (Bytes > "10KB", Perms == "rw-r--r--",
# FsPath / "x") elementwise onto the columns.
BytesArray._add_comparison_ops()
BytesArray._add_arithmetic_ops()
PermsArray._add_comparison_ops()
PathArray._add_comparison_ops()
PathArray._add_arithmetic_ops()
