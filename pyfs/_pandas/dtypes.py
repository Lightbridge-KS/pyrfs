"""ExtensionDtypes for the pyfs typed scalars.

Registered names: ``"bytes"``, ``"perms"``, ``"path"`` — so columns can be
built with ``series.astype("bytes")`` etc.
"""

from __future__ import annotations

import builtins

from pandas.api.extensions import ExtensionDtype, register_extension_dtype

from pyfs.fspath import FsPath
from pyfs.values import Bytes, Perms

__all__ = ["BytesDtype", "PathDtype", "PermsDtype"]


@register_extension_dtype
class BytesDtype(ExtensionDtype):
    """Column dtype for human-readable byte sizes (``445.2K``)."""

    name = "bytes"
    type = Bytes

    @classmethod
    def construct_array_type(cls) -> builtins.type:  # `type` attr shadows the builtin
        from pyfs._pandas.arrays import BytesArray

        return BytesArray


@register_extension_dtype
class PermsDtype(ExtensionDtype):
    """Column dtype for permission bits displayed as ``rwxr-xr-x``."""

    name = "perms"
    type = Perms

    @classmethod
    def construct_array_type(cls) -> builtins.type:  # `type` attr shadows the builtin
        from pyfs._pandas.arrays import PermsArray

        return PermsArray


@register_extension_dtype
class PathDtype(ExtensionDtype):
    """Column dtype for tidy ``FsPath`` values."""

    name = "path"
    type = FsPath

    @classmethod
    def construct_array_type(cls) -> builtins.type:  # `type` attr shadows the builtin
        from pyfs._pandas.arrays import PathArray

        return PathArray
