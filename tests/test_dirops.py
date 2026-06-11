"""Directory operations: traversal, filtering, tree, copy/delete."""

import os
import pathlib

import pytest

import pyfs as fs
from pyfs import FsPath, FsValueError


@pytest.fixture
def base(tmp_path: pathlib.Path) -> FsPath:
    """A small tree:

    base/
    ├── .hidden.txt
    ├── a.py
    ├── b.txt
    └── sub/
        ├── c.py
        └── deep/
            └── d.md
    """
    root = FsPath(str(tmp_path))
    fs.file_touch([root / ".hidden.txt", root / "a.py", root / "b.txt"])
    fs.dir_create(root / "sub/deep")
    fs.file_touch([root / "sub/c.py", root / "sub/deep/d.md"])
    return root


def names(paths: list[FsPath], base: FsPath) -> list[str]:
    return [p.rel_to(base) for p in paths]


class TestDirCreateDelete:
    def test_create_recurse_default(self, base: FsPath) -> None:
        p = fs.dir_create(base / "x/y/z")
        assert os.path.isdir(p)

    def test_create_idempotent(self, base: FsPath) -> None:
        fs.dir_create(base / "once")
        assert fs.dir_create(base / "once") == base / "once"

    def test_create_no_recurse_missing_parent(self, base: FsPath) -> None:
        with pytest.raises(FileNotFoundError):
            fs.dir_create(base / "missing/child", recurse=False)

    def test_exists(self, base: FsPath) -> None:
        assert fs.dir_exists(base / "sub")
        assert not fs.dir_exists(base / "a.py")

    def test_delete_recursive(self, base: FsPath) -> None:
        fs.dir_delete(base / "sub")
        assert not os.path.exists(base / "sub")


class TestDirLs:
    def test_default_non_recursive_no_hidden(self, base: FsPath) -> None:
        assert names(fs.dir_ls(base), base) == ["a.py", "b.txt", "sub"]

    def test_all_includes_hidden(self, base: FsPath) -> None:
        assert ".hidden.txt" in names(fs.dir_ls(base, all=True), base)

    def test_recurse_true(self, base: FsPath) -> None:
        out = names(fs.dir_ls(base, recurse=True), base)
        assert out == ["a.py", "b.txt", "sub", "sub/c.py", "sub/deep", "sub/deep/d.md"]

    def test_recurse_depth_1(self, base: FsPath) -> None:
        out = names(fs.dir_ls(base, recurse=1), base)
        assert out == ["a.py", "b.txt", "sub", "sub/c.py", "sub/deep"]

    def test_type_filter(self, base: FsPath) -> None:
        assert names(fs.dir_ls(base, type="directory"), base) == ["sub"]
        files = names(fs.dir_ls(base, recurse=True, type="file"), base)
        assert files == ["a.py", "b.txt", "sub/c.py", "sub/deep/d.md"]

    def test_type_unknown_raises(self, base: FsPath) -> None:
        with pytest.raises(FsValueError, match="unknown `type`"):
            fs.dir_ls(base, type="wormhole")

    def test_glob(self, base: FsPath) -> None:
        out = names(fs.dir_ls(base, recurse=True, glob="*.py"), base)
        assert out == ["a.py", "sub/c.py"]

    def test_regexp(self, base: FsPath) -> None:
        out = names(fs.dir_ls(base, recurse=True, regexp=r"\.md$"), base)
        assert out == ["sub/deep/d.md"]

    def test_invert(self, base: FsPath) -> None:
        out = names(fs.dir_ls(base, glob="*.py", invert=True), base)
        assert out == ["b.txt", "sub"]

    def test_glob_and_regexp_raises(self, base: FsPath) -> None:
        with pytest.raises(FsValueError, match="cannot both be set"):
            fs.dir_ls(base, glob="*.py", regexp=r"\.py$")

    def test_missing_dir_raises(self, base: FsPath) -> None:
        with pytest.raises(FileNotFoundError):
            fs.dir_ls(base / "nope")

    def test_fail_false_warns_and_returns(self, base: FsPath) -> None:
        with pytest.warns(UserWarning, match="unreadable"):
            out = fs.dir_ls(base / "nope", fail=False)
        assert out == []

    def test_fail_false_skips_unreadable_subdir(self, base: FsPath) -> None:
        locked = base / "sub/locked"
        os.mkdir(locked)
        os.chmod(locked, 0o000)
        try:
            with pytest.warns(UserWarning):
                out = fs.dir_ls(base, recurse=True, fail=False)
            assert str(locked.rel_to(base)) in names(out, base)
        finally:
            os.chmod(locked, 0o755)


class TestWalkMapInfo:
    def test_walk_is_lazy(self, base: FsPath) -> None:
        gen = fs.dir_walk(base)
        assert next(gen) == base / "a.py"

    def test_map(self, base: FsPath) -> None:
        out = fs.dir_map(base, lambda p: p.name(), glob="*.py")
        assert out == ["a.py"]

    def test_info_rows(self, base: FsPath) -> None:
        # engine rows; the public fs.dir_info upgrades to a DataFrame with pandas
        from pyfs._engine.dirops import dir_info as engine_dir_info

        rows = engine_dir_info(base, recurse=True, type="file")
        assert all(r["type"] == "file" for r in rows)
        assert any(str(r["path"]).endswith("d.md") for r in rows)


class TestDirTree:
    def test_tree_output(self, base: FsPath, capsys: pytest.CaptureFixture[str]) -> None:
        fs.dir_tree(base)
        out = capsys.readouterr().out
        assert out.splitlines()[0] == str(base)
        assert "├── a.py" in out
        assert "└── sub" in out
        assert "    └── deep" in out
        assert "        └── d.md" in out
        assert ".hidden.txt" not in out

    def test_tree_depth_limited(self, base: FsPath, capsys: pytest.CaptureFixture[str]) -> None:
        fs.dir_tree(base, recurse=1)
        out = capsys.readouterr().out
        assert "c.py" in out
        assert "d.md" not in out


class TestDirCopy:
    def test_copy_tree(self, base: FsPath) -> None:
        dest = fs.dir_copy(base / "sub", base / "sub2")
        assert os.path.isfile(dest / "c.py")
        assert os.path.isfile(dest / "deep/d.md")

    def test_copy_into_existing_dir(self, base: FsPath) -> None:
        os.mkdir(base / "out")
        dest = fs.dir_copy(base / "sub", base / "out")
        assert dest == base / "out/sub"
        assert os.path.isfile(dest / "c.py")

    def test_second_copy_nests_like_cp(self, base: FsPath) -> None:
        fs.dir_copy(base / "sub", base / "sub2")
        dest = fs.dir_copy(base / "sub", base / "sub2")  # sub2 exists -> copy into it
        assert dest == base / "sub2/sub"

    def test_overwrite_guard(self, base: FsPath) -> None:
        os.mkdir(base / "out")
        fs.dir_copy(base / "sub", base / "out")  # -> out/sub
        with pytest.raises(FileExistsError):
            fs.dir_copy(base / "sub", base / "out")  # resolved target out/sub exists
        dest = fs.dir_copy(base / "sub", base / "out", overwrite=True)
        assert os.path.isfile(dest / "c.py")

    def test_source_must_be_dir(self, base: FsPath) -> None:
        with pytest.raises(NotADirectoryError):
            fs.dir_copy(base / "a.py", base / "nope")

    def test_no_dir_move_dirs_move_via_file_move(self, base: FsPath) -> None:
        assert not hasattr(fs, "dir_move")
        dest = fs.file_move(base / "sub", base / "moved")
        assert os.path.isfile(dest / "c.py")


class TestFluentSurface:
    def test_mkdir_touch_ls_chain(self, base: FsPath) -> None:
        project = (base / "project").mkdir().touch_file("README.md").touch_file("setup.py")
        assert project == base / "project"
        assert names(project.ls(glob="*.py"), project) == ["setup.py"]

    def test_walk_and_tree(self, base: FsPath, capsys: pytest.CaptureFixture[str]) -> None:
        assert sorted(p.ext() for p in (base / "sub").walk(type="file")) == ["md", "py"]
        (base / "sub").tree()
        assert "c.py" in capsys.readouterr().out

    def test_rmdir(self, base: FsPath) -> None:
        (base / "sub").rmdir()
        assert not os.path.exists(base / "sub")
