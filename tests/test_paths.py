"""Path algebra — the path_* family."""

import os
from typing import ClassVar

import pytest

import pyrfs as fs
from pyrfs import FsPath, FsValueError


class TestPath:
    def test_basic_join(self) -> None:
        p = fs.path("foo", "bar", "a", ext="txt")
        assert p == "foo/bar/a.txt"
        assert isinstance(p, FsPath)

    def test_ext_with_dot(self) -> None:
        assert fs.path("a", ext=".txt") == "a.txt"

    def test_concat_semantics_not_join_reset(self) -> None:
        # unlike os.path.join, an absolute later part does not reset the path
        assert fs.path("a", "/b") == "a/b"

    def test_messy_parts_are_tidied(self) -> None:
        assert fs.path("a/", "/b/", "c//d") == "a/b/c/d"

    def test_empty(self) -> None:
        assert fs.path() == ""


class TestExt:
    def test_ext(self) -> None:
        assert fs.path_ext("a.txt") == "txt"
        assert fs.path_ext("a.tar.gz") == "gz"
        assert fs.path_ext("a") == ""
        assert fs.path_ext(".gitignore") == ""
        assert fs.path_ext("dir.d/file") == ""

    def test_ext_remove(self) -> None:
        assert fs.path_ext_remove("a.txt") == "a"
        assert fs.path_ext_remove(".gitignore") == ".gitignore"
        assert fs.path_ext_remove("d/a.tar.gz") == "d/a.tar"

    def test_ext_set(self) -> None:
        assert fs.path_ext_set("report.md", "html") == "report.html"
        assert fs.path_ext_set("report", "html") == "report.html"
        assert fs.path_ext_set("report.md", ".html") == "report.html"
        assert fs.path_ext_set("report.md", "") == "report"

    def test_ext_round_trip(self) -> None:
        p = "data/x.csv"
        assert fs.path_ext_set(fs.path_ext_remove(p), fs.path_ext(p)) == p

    def test_vectorized(self) -> None:
        assert fs.path_ext(["a.txt", "b.md"]) == ["txt", "md"]
        assert fs.path_ext_set(["a.txt", "b"], "py") == ["a.py", "b.py"]


class TestFileDir:
    def test_file(self) -> None:
        assert fs.path_file("a/b/c.txt") == "c.txt"
        assert fs.path_file("c.txt") == "c.txt"

    def test_dir(self) -> None:
        assert fs.path_dir("a/b/c.txt") == "a/b"
        assert fs.path_dir("c.txt") == "."
        assert fs.path_dir("/a") == "/"


class TestSplitJoin:
    def test_split_relative(self) -> None:
        assert fs.path_split("a/b/c") == ["a", "b", "c"]

    def test_split_absolute(self) -> None:
        assert fs.path_split("/usr/bin") == ["/", "usr", "bin"]
        assert fs.path_split("/") == ["/"]

    def test_join_inverse_of_split(self) -> None:
        for p in ["a/b/c", "/usr/bin", "x"]:
            assert fs.path_join(fs.path_split(p)) == p

    def test_join_nested(self) -> None:
        assert fs.path_join([["a", "b"], ["c", "d"]]) == ["a/b", "c/d"]

    def test_split_vectorized(self) -> None:
        assert fs.path_split(["a/b", "c"]) == [["a", "b"], ["c"]]


class TestRelCommon:
    def test_rel(self) -> None:
        assert fs.path_rel("/a/b/c", "/a") == "b/c"
        assert fs.path_rel("a/b", "a") == "b"
        assert fs.path_rel("/a/b", "/a/d") == "../b"

    def test_common(self) -> None:
        assert fs.path_common(["a/b/c", "a/b/d"]) == "a/b"
        assert fs.path_common(["/x/y", "/x/z/w"]) == "/x"
        assert fs.path_common(["a/b"]) == "a/b"

    def test_common_mixed_raises(self) -> None:
        with pytest.raises(FsValueError):
            fs.path_common(["/abs", "rel"])

    def test_common_empty_raises(self) -> None:
        with pytest.raises(FsValueError):
            fs.path_common([])


class TestFilter:
    paths: ClassVar[list[str]] = ["a.py", "b.txt", "src/c.py", "src/d.md"]

    def test_glob(self) -> None:
        assert fs.path_filter(self.paths, glob="*.py") == ["a.py", "src/c.py"]

    def test_regexp(self) -> None:
        assert fs.path_filter(self.paths, regexp=r"\.md$") == ["src/d.md"]

    def test_invert(self) -> None:
        assert fs.path_filter(self.paths, glob="*.py", invert=True) == ["b.txt", "src/d.md"]

    def test_both_set_raises(self) -> None:
        with pytest.raises(FsValueError, match="cannot both be set"):
            fs.path_filter(self.paths, glob="*.py", regexp=r"\.py$")

    def test_no_filter_returns_all_tidied(self) -> None:
        out = fs.path_filter(["a//b/"])
        assert out == ["a/b"]
        assert isinstance(out[0], FsPath)


class TestHasParent:
    def test_relative(self) -> None:
        assert fs.path_has_parent("a/b", "a")
        assert not fs.path_has_parent("a", "b")

    def test_absolute(self) -> None:
        assert fs.path_has_parent("/x/y", "/x")
        assert fs.path_has_parent("/x/y", "/")
        assert not fs.path_has_parent("/xy/z", "/x")

    def test_vectorized(self) -> None:
        assert fs.path_has_parent(["a/b", "c/d"], "a") == [True, False]


class TestSanitize:
    def test_illegal_chars(self) -> None:
        assert fs.path_sanitize("a/b:c*d") == "abcd"

    def test_replacement(self) -> None:
        assert fs.path_sanitize("a/b", "_") == "a_b"

    def test_control_chars(self) -> None:
        assert fs.path_sanitize("a\x00b\x1fc") == "abc"

    def test_windows_reserved(self) -> None:
        assert fs.path_sanitize("CON") == ""
        assert fs.path_sanitize("aux.txt") == ""

    def test_trailing_dots_spaces(self) -> None:
        assert fs.path_sanitize("name. . ") == "name"

    def test_dots_only(self) -> None:
        assert fs.path_sanitize("..") == ""

    def test_truncates(self) -> None:
        assert len(fs.path_sanitize("x" * 300)) == 255


class TestResolution:
    def test_norm(self) -> None:
        assert fs.path_norm("a/../b") == "b"
        assert fs.path_norm("./a/./b") == "a/b"

    def test_abs(self) -> None:
        p = fs.path_abs("x")
        assert p.startswith("/")
        assert p.endswith("/x")

    def test_real_resolves_symlink(self, tmp_path: object) -> None:
        import pathlib

        base = pathlib.Path(str(tmp_path))
        target = base / "target.txt"
        target.write_text("hi")
        link = base / "link.txt"
        link.symlink_to(target)
        assert fs.path_real(str(link)) == fs.path_real(str(target))

    def test_expand(self) -> None:
        home = os.path.expanduser("~").replace("\\", "/")
        assert fs.path_expand("~/x") == f"{home}/x"

    def test_home_temp_wd(self) -> None:
        assert isinstance(fs.path_home(), FsPath)
        assert fs.path_home("a").endswith("/a")
        assert isinstance(fs.path_temp(), FsPath)
        assert fs.path_wd() == os.getcwd().replace("\\", "/")

    def test_tidy_export(self) -> None:
        assert fs.path_tidy("a//b/") == "a/b"
        assert fs.path_tidy(["a//", "b"]) == ["a", "b"]
