"""File operations — both functional and fluent surfaces, in tmp_path."""

import os
import pathlib
import stat

import pytest

import pyfs as fs
from pyfs import Bytes, FsPath, FsValueError, Perms


@pytest.fixture
def base(tmp_path: pathlib.Path) -> FsPath:
    return FsPath(str(tmp_path))


class TestCreateTouch:
    def test_create(self, base: FsPath) -> None:
        p = fs.file_create(base / "a.txt")
        assert isinstance(p, FsPath)
        assert os.path.isfile(p)

    def test_create_leaves_existing_content(self, base: FsPath) -> None:
        p = base / "a.txt"
        with open(p, "w") as fh:
            fh.write("keep me")
        fs.file_create(p)
        with open(p) as fh:
            assert fh.read() == "keep me"

    def test_create_with_mode(self, base: FsPath) -> None:
        p = fs.file_create(base / "ro.txt", mode="600")
        assert stat.S_IMODE(os.stat(p).st_mode) == 0o600

    def test_create_vectorized(self, base: FsPath) -> None:
        out = fs.file_create([base / "x", base / "y"])
        assert all(os.path.isfile(p) for p in out)

    def test_touch_creates_and_updates(self, base: FsPath) -> None:
        p = base / "t.txt"
        fs.file_touch(p)
        assert os.path.isfile(p)
        os.utime(p, (0, 0))
        fs.file_touch(p)
        assert os.stat(p).st_mtime > 0


class TestCopy:
    def test_copy_returns_new_path(self, base: FsPath) -> None:
        src = fs.file_create(base / "a.txt")
        dest = fs.file_copy(src, base / "b.txt")
        assert dest == base / "b.txt"
        assert os.path.isfile(dest)

    def test_copy_into_existing_dir(self, base: FsPath) -> None:
        src = fs.file_create(base / "a.txt")
        os.mkdir(base / "out")
        dest = fs.file_copy(src, base / "out")
        assert dest == base / "out/a.txt"
        assert os.path.isfile(dest)

    def test_copy_overwrite_guard(self, base: FsPath) -> None:
        src = fs.file_create(base / "a.txt")
        fs.file_create(base / "b.txt")
        with pytest.raises(FileExistsError):
            fs.file_copy(src, base / "b.txt")
        dest = fs.file_copy(src, base / "b.txt", overwrite=True)
        assert os.path.isfile(dest)

    def test_copy_preserves_content(self, base: FsPath) -> None:
        src = base / "a.txt"
        with open(src, "w") as fh:
            fh.write("payload")
        dest = fs.file_copy(src, base / "b.txt")
        with open(dest) as fh:
            assert fh.read() == "payload"


class TestMoveDelete:
    def test_move(self, base: FsPath) -> None:
        src = fs.file_create(base / "a.txt")
        dest = fs.file_move(src, base / "b.txt")
        assert dest == base / "b.txt"
        assert not os.path.exists(src)
        assert os.path.exists(dest)

    def test_move_overwrite_guard(self, base: FsPath) -> None:
        src = fs.file_create(base / "a.txt")
        fs.file_create(base / "b.txt")
        with pytest.raises(FileExistsError):
            fs.file_move(src, base / "b.txt")

    def test_move_directory(self, base: FsPath) -> None:
        os.mkdir(base / "d")
        fs.file_create(base / "d" / "inner.txt")
        dest = fs.file_move(base / "d", base / "e")
        assert os.path.isdir(dest)
        assert os.path.isfile(dest / "inner.txt")

    def test_delete(self, base: FsPath) -> None:
        p = fs.file_create(base / "a.txt")
        out = fs.file_delete(p)
        assert out == p
        assert not os.path.exists(p)

    def test_delete_missing_raises(self, base: FsPath) -> None:
        with pytest.raises(FileNotFoundError):
            fs.file_delete(base / "nope.txt")


class TestQueries:
    def test_exists(self, base: FsPath) -> None:
        p = fs.file_create(base / "a.txt")
        assert fs.file_exists(p)
        assert not fs.file_exists(base / "nope")
        assert fs.file_exists([p, base / "nope"]) == [True, False]

    def test_access(self, base: FsPath) -> None:
        p = fs.file_create(base / "a.txt")
        assert fs.file_access(p)
        assert fs.file_access(p, "read")
        with pytest.raises(FsValueError):
            fs.file_access(p, "fly")

    def test_size_is_bytes(self, base: FsPath) -> None:
        p = base / "a.bin"
        with open(p, "wb") as fh:
            fh.write(b"x" * 2048)
        size = fs.file_size(p)
        assert isinstance(size, Bytes)
        assert size == 2048
        assert size == "2K"
        assert size > "1K"

    def test_chmod_absolute_and_symbolic(self, base: FsPath) -> None:
        p = fs.file_create(base / "run.sh", mode="644")
        fs.file_chmod(p, "600")
        assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
        fs.file_chmod(p, "u+x")
        assert stat.S_IMODE(os.stat(p).st_mode) == 0o700

    def test_info_row_types(self, base: FsPath) -> None:
        p = fs.file_create(base / "a.txt")
        rows = fs.file_info(p)
        assert len(rows) == 1
        row = rows[0]
        assert row["path"] == p
        assert row["type"] == "file"
        assert isinstance(row["size"], Bytes)
        assert isinstance(row["permissions"], Perms)

    def test_info_many(self, base: FsPath) -> None:
        ps = fs.file_create([base / "x", base / "y"])
        rows = fs.file_info(ps)
        assert [r["path"] for r in rows] == ps


class TestFluentSurface:
    def test_lifecycle_chain(self, base: FsPath) -> None:
        p = (base / "data.csv").create()
        copy = p.copy_to(base / "backup.csv")
        assert copy.exists()
        moved = copy.move_to(base / "final.csv")
        assert moved.exists() and not copy.exists()
        assert isinstance(moved.size(), Bytes)
        moved.delete()
        assert not moved.exists()

    def test_touch_and_info(self, base: FsPath) -> None:
        p = (base / "t.txt").touch()
        assert p.exists()
        assert p.info()["type"] == "file"

    def test_chmod_chain(self, base: FsPath) -> None:
        p = (base / "s.sh").create().chmod("u+x")
        assert p.access("execute")
