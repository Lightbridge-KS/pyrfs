"""Link operations: create/read/copy/delete symlinks."""

import os
import pathlib

import pytest

import pyfs as fs
from pyfs import FsPath, FsValueError


@pytest.fixture
def base(tmp_path: pathlib.Path) -> FsPath:
    root = FsPath(str(tmp_path))
    fs.file_touch(root / "target.txt")
    return root


class TestLinkCreate:
    def test_symbolic_round_trip(self, base: FsPath) -> None:
        link = fs.link_create(base / "target.txt", base / "ln.txt")
        assert fs.link_exists(link)
        assert fs.link_path(link) == base / "target.txt"

    def test_hard_link(self, base: FsPath) -> None:
        link = fs.link_create(base / "target.txt", base / "hard.txt", symbolic=False)
        assert not fs.link_exists(link)  # hard links are not symlinks
        assert os.stat(link).st_ino == os.stat(base / "target.txt").st_ino

    def test_existing_target_raises(self, base: FsPath) -> None:
        fs.file_touch(base / "busy.txt")
        with pytest.raises(FileExistsError):
            fs.link_create(base / "target.txt", base / "busy.txt")


class TestLinkQueries:
    def test_link_exists_only_for_links(self, base: FsPath) -> None:
        assert not fs.link_exists(base / "target.txt")
        assert not fs.link_exists(base / "nope")

    def test_broken_link_still_exists(self, base: FsPath) -> None:
        link = fs.link_create(base / "ghost.txt", base / "broken.txt")
        assert fs.link_exists(link)
        assert fs.file_exists(link)  # lexists semantics

    def test_link_path_on_non_link_raises(self, base: FsPath) -> None:
        with pytest.raises(OSError):
            fs.link_path(base / "target.txt")


class TestLinkCopyDelete:
    def test_copy_points_to_same_target(self, base: FsPath) -> None:
        ln = fs.link_create(base / "target.txt", base / "ln.txt")
        ln2 = fs.link_copy(ln, base / "ln2.txt")
        assert fs.link_path(ln2) == fs.link_path(ln)

    def test_copy_overwrite_guard(self, base: FsPath) -> None:
        ln = fs.link_create(base / "target.txt", base / "ln.txt")
        fs.file_touch(base / "busy.txt")
        with pytest.raises(FileExistsError):
            fs.link_copy(ln, base / "busy.txt")
        out = fs.link_copy(ln, base / "busy.txt", overwrite=True)
        assert fs.link_exists(out)

    def test_delete_leaves_target(self, base: FsPath) -> None:
        ln = fs.link_create(base / "target.txt", base / "ln.txt")
        fs.link_delete(ln)
        assert not os.path.lexists(ln)
        assert os.path.exists(base / "target.txt")

    def test_delete_refuses_non_link(self, base: FsPath) -> None:
        with pytest.raises(FsValueError, match="not a symlink"):
            fs.link_delete(base / "target.txt")
