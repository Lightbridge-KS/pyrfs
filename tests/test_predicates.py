"""is_* predicates and user/group id lookups."""

import pathlib
import sys

import pytest

import pyfs as fs
from pyfs import FsPath


@pytest.fixture
def base(tmp_path: pathlib.Path) -> FsPath:
    root = FsPath(str(tmp_path))
    fs.file_touch(root / "file.txt")
    fs.dir_create(root / "dir")
    fs.link_create(root / "file.txt", root / "link.txt")
    return root


class TestTypePredicates:
    def test_is_file(self, base: FsPath) -> None:
        assert fs.is_file(base / "file.txt")
        assert not fs.is_file(base / "dir")
        assert not fs.is_file(base / "link.txt")  # lstat semantics, like fs
        assert not fs.is_file(base / "nope")

    def test_is_dir(self, base: FsPath) -> None:
        assert fs.is_dir(base / "dir")
        assert not fs.is_dir(base / "file.txt")
        assert not fs.is_dir(base / "nope")

    def test_is_link(self, base: FsPath) -> None:
        assert fs.is_link(base / "link.txt")
        assert not fs.is_link(base / "file.txt")

    def test_vectorized(self, base: FsPath) -> None:
        out = fs.is_file([base / "file.txt", base / "dir", base / "nope"])
        assert out == [True, False, False]

    def test_fluent(self, base: FsPath) -> None:
        assert (base / "file.txt").is_file()
        assert (base / "dir").is_dir()
        assert (base / "link.txt").is_link()


class TestEmptyPredicates:
    def test_is_file_empty(self, base: FsPath) -> None:
        assert fs.is_file_empty(base / "file.txt")
        with open(base / "file.txt", "w") as fh:
            fh.write("x")
        assert not fs.is_file_empty(base / "file.txt")
        assert not fs.is_file_empty(base / "nope")

    def test_is_dir_empty(self, base: FsPath) -> None:
        assert fs.is_dir_empty(base / "dir")
        fs.file_touch(base / "dir/.dot")  # hidden entries count
        assert not fs.is_dir_empty(base / "dir")
        assert not fs.is_dir_empty(base / "nope")


class TestIsAbsolutePath:
    def test_absolute_forms(self) -> None:
        assert fs.is_absolute_path("/usr/bin")
        assert fs.is_absolute_path("~/data")  # ~ counts, as in fs
        assert not fs.is_absolute_path("rel/path")

    def test_vectorized(self) -> None:
        assert fs.is_absolute_path(["/a", "b"]) == [True, False]


class TestIds:
    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX only")
    def test_user_ids(self) -> None:
        rows = fs.user_ids()
        assert rows
        assert {"user_id", "user_name"} <= rows[0].keys()
        assert any(r["user_id"] == 0 for r in rows)  # root

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX only")
    def test_group_ids(self) -> None:
        rows = fs.group_ids()
        assert rows
        assert {"group_id", "group_name"} <= rows[0].keys()
