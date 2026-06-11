"""Public *_info surface: list[dict] without pandas, DataFrame with it.

The DataFrame half lives in test_pandas.py; this file pins the core mode.
"""

import pathlib

import pytest

import pyrfs as fs
from pyrfs import Bytes, FsPath, has_pandas


@pytest.mark.skipif(has_pandas(), reason="pandas installed: DataFrame surface applies")
class TestCoreMode:
    def test_file_info_returns_rows(self, tmp_path: pathlib.Path) -> None:
        p = fs.file_touch(FsPath(str(tmp_path)) / "a.txt")
        rows = fs.file_info(p)
        assert isinstance(rows, list)
        assert rows[0]["type"] == "file"
        assert isinstance(rows[0]["size"], Bytes)

    def test_dir_info_returns_rows(self, tmp_path: pathlib.Path) -> None:
        base = FsPath(str(tmp_path))
        fs.file_touch(base / "a.txt")
        rows = fs.dir_info(base)
        assert isinstance(rows, list)
        assert len(rows) == 1
