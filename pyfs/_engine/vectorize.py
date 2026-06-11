"""Polymorphic dispatch: scalar path functions that also map over collections.

R's fs is vectorized end to end; Python is scalar-by-default. The
``@vectorized`` decorator bridges the gap: a function written for a single
path transparently accepts a list/tuple/set (returning a ``list``) or a
pandas ``Series`` (returning a ``Series``) — without pyfs ever importing
pandas (the Series branch only activates when pandas is already loaded).
"""

from __future__ import annotations

import functools
import os
import sys
from collections.abc import Callable, Iterable
from typing import Concatenate, Generic, ParamSpec, Protocol, TypeVar, cast, overload

__all__ = ["PathInput", "Vectorized", "vectorized"]

P = ParamSpec("P")
R = TypeVar("R")

PathInput = str | os.PathLike[str]
"""A single path-like input accepted everywhere pyfs takes a path."""


class _SeriesLike(Protocol):
    """The slice of the pandas Series API we use (duck-typed, no import)."""

    def map(self, arg: Callable[[str], object]) -> object: ...


class Vectorized(Generic[P, R]):
    """Callable wrapper produced by :func:`vectorized`.

    Dispatches on the first argument:

    - ``str | os.PathLike`` -> scalar result
    - pandas ``Series`` (if pandas is loaded) -> ``Series``
    - any other iterable (list/tuple/set, ...) -> ``list``
    """

    def __init__(self, func: Callable[Concatenate[str, P], R]) -> None:
        self._func = func
        functools.update_wrapper(self, func)

    # str overlaps Iterable[str]; scalar-first order is intended (a str is one path).
    @overload
    def __call__(  # type: ignore[overload-overlap]
        self, path: PathInput, /, *args: P.args, **kwargs: P.kwargs
    ) -> R: ...

    @overload
    def __call__(
        self, path: Iterable[PathInput], /, *args: P.args, **kwargs: P.kwargs
    ) -> list[R]: ...

    def __call__(
        self, path: PathInput | Iterable[PathInput], /, *args: P.args, **kwargs: P.kwargs
    ) -> object:
        if isinstance(path, (str, os.PathLike)):
            return self._func(os.fspath(path), *args, **kwargs)
        pd = sys.modules.get("pandas")
        if pd is not None and isinstance(path, pd.Series):
            series = cast("_SeriesLike", path)
            return series.map(lambda p: self._func(p, *args, **kwargs))
        return [self._func(os.fspath(p), *args, **kwargs) for p in path]


def vectorized(func: Callable[Concatenate[str, P], R]) -> Vectorized[P, R]:
    """Make a scalar path function polymorphic over collections and Series."""
    return Vectorized(func)
