"""@vectorized dispatch: scalar, collection, PathLike, and (optional) Series."""

import pathlib

import pytest

from pyrfs._engine.vectorize import vectorized


@vectorized
def shout(path: str, suffix: str = "!") -> str:
    return path.upper() + suffix


def test_scalar_str() -> None:
    assert shout("a/b") == "A/B!"


def test_scalar_pathlike() -> None:
    assert shout(pathlib.PurePosixPath("a/b")) == "A/B!"


def test_list_in_list_out() -> None:
    assert shout(["a", "b"]) == ["A!", "B!"]


def test_tuple_in_list_out() -> None:
    assert shout(("a", "b")) == ["A!", "B!"]


def test_set_in_list_out() -> None:
    assert sorted(shout({"a", "b"})) == ["A!", "B!"]


def test_extra_args_pass_through() -> None:
    assert shout(["a"], suffix="?") == ["A?"]


def test_wraps_metadata() -> None:
    assert shout.__name__ == "shout"


def test_series_in_series_out() -> None:
    pd = pytest.importorskip("pandas")
    out = shout(pd.Series(["a", "b"]))
    assert isinstance(out, pd.Series)
    assert out.tolist() == ["A!", "B!"]
