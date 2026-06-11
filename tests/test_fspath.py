"""FsPath — fluent surface: construction, chaining, str interop."""

import os
import pathlib

from pyrfs import FsPath


class TestConstruction:
    def test_tidies_on_creation(self) -> None:
        assert FsPath("a//b/") == "a/b"

    def test_is_a_str(self) -> None:
        p = FsPath("a/b")
        assert isinstance(p, str)
        assert os.fspath(p) == "a/b"

    def test_from_pathlike(self) -> None:
        assert FsPath(pathlib.PurePosixPath("a/b")) == "a/b"

    def test_empty_default(self) -> None:
        assert FsPath() == ""

    def test_repr(self) -> None:
        assert repr(FsPath("a/b")) == "FsPath('a/b')"


class TestJoining:
    def test_truediv_chain(self) -> None:
        p = FsPath("foo") / "bar" / "a.txt"
        assert p == "foo/bar/a.txt"
        assert isinstance(p, FsPath)

    def test_rtruediv_from_plain_str(self) -> None:
        p = "a" / FsPath("b")
        assert p == "a/b"
        assert isinstance(p, FsPath)

    def test_join_tidies(self) -> None:
        assert FsPath("a/") / "/b" == "a/b"


class TestMethods:
    def test_ext_family(self) -> None:
        p = FsPath("data/raw.csv")
        assert p.ext() == "csv"
        assert p.with_ext("parquet") == "data/raw.parquet"
        assert p.with_ext("") == "data/raw"

    def test_dir_name(self) -> None:
        p = FsPath("a/b/c.txt")
        assert p.dir() == "a/b"
        assert p.name() == "c.txt"

    def test_parts(self) -> None:
        assert FsPath("/usr/bin").parts() == ["/", "usr", "bin"]

    def test_rel_to(self) -> None:
        assert FsPath("/a/b/c").rel_to("/a") == "b/c"

    def test_has_parent(self) -> None:
        assert FsPath("a/b").has_parent("a")

    def test_norm(self) -> None:
        assert FsPath("a/../b").norm() == "b"

    def test_chaining_returns_fspath(self) -> None:
        out = (FsPath("data") / "raw.csv").with_ext("parquet").dir()
        assert out == "data"
        assert isinstance(out, FsPath)

    def test_as_pathlib(self) -> None:
        pl = FsPath("a/b").as_pathlib()
        assert isinstance(pl, pathlib.Path)
        assert str(pl) == os.path.join("a", "b")


class TestStrInterop:
    def test_str_methods_untouched(self) -> None:
        # str.split must NOT be shadowed — FsPath is a str first
        assert FsPath("a/b").split("/") == ["a", "b"]
        assert FsPath("a/b").startswith("a")
        assert FsPath("A").lower() == "a"

    def test_hash_and_equality_with_str(self) -> None:
        assert hash(FsPath("a/b")) == hash("a/b")
        assert FsPath("a/b") in {"a/b"}

    def test_open_interop(self, tmp_path: pathlib.Path) -> None:
        p = FsPath(str(tmp_path)) / "f.txt"
        with open(p, "w") as fh:
            fh.write("hello")
        assert (tmp_path / "f.txt").read_text() == "hello"
