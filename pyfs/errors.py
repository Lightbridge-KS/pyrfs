"""pyfs error hierarchy for validation failures.

OS-level failures raise native :class:`OSError` subclasses
(``FileNotFoundError``, ``FileExistsError``, ``PermissionError``).
``FsError`` and friends cover pyfs-level argument validation that has no
native equivalent.
"""

from __future__ import annotations

__all__ = ["FsError", "FsValueError"]


class FsError(Exception):
    """Base class for all pyfs validation errors."""


class FsValueError(FsError, ValueError):
    """An argument value (or combination of arguments) is invalid."""
