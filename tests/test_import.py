"""Smoke test: the package imports and carries a version."""

import pyfs


def test_import() -> None:
    assert isinstance(pyfs.__version__, str)
    assert pyfs.__version__
