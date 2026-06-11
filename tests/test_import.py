"""Smoke test: the package imports and carries a version."""

import pyrfs


def test_import() -> None:
    assert isinstance(pyrfs.__version__, str)
    assert pyrfs.__version__
