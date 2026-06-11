"""pandas layer: ExtensionDtypes, .fs accessor, typed *_info DataFrames."""

import pathlib

import pytest

pd = pytest.importorskip("pandas")

import pyfs as fs  # noqa: E402
from pyfs import Bytes, FsPath, Perms  # noqa: E402
from pyfs._pandas.arrays import BytesArray, PathArray, PermsArray  # noqa: E402


@pytest.fixture
def base(tmp_path: pathlib.Path) -> FsPath:
    root = FsPath(str(tmp_path))
    with open(root / "big.bin", "wb") as fh:
        fh.write(b"x" * 4096)
    with open(root / "small.txt", "wb") as fh:
        fh.write(b"y" * 10)
    fs.dir_create(root / "sub")
    return root


class TestBytesColumn:
    def test_construct_from_strings(self) -> None:
        s = pd.Series(["1K", "10MB", "455"], dtype="bytes")
        assert s.dtype.name == "bytes"
        assert s[0] == Bytes("1K")
        assert isinstance(s[0], Bytes)

    def test_compares_against_literal(self) -> None:
        s = pd.Series([512, 2048, 4096], dtype="bytes")
        assert (s > "1K").tolist() == [False, True, True]
        assert (s == "2KB").tolist() == [False, True, False]

    def test_reductions(self) -> None:
        s = pd.Series(["1K", "3K"], dtype="bytes")
        assert s.sum() == Bytes("4K")
        assert isinstance(s.sum(), Bytes)
        assert s.min() == Bytes("1K")
        assert s.max() == Bytes("3K")

    def test_sorting(self) -> None:
        s = pd.Series(["1M", "1K", "1G"], dtype="bytes")
        assert s.sort_values().tolist() == [Bytes("1K"), Bytes("1M"), Bytes("1G")]

    def test_repr_is_humanized(self) -> None:
        s = pd.Series([455200], dtype="bytes")
        assert "444.5K" in repr(s)

    def test_arithmetic_stays_bytes(self) -> None:
        s = pd.Series(["1K", "2K"], dtype="bytes")
        doubled = s + s
        assert doubled.dtype.name == "bytes"
        assert doubled.tolist() == [Bytes("2K"), Bytes("4K")]

    def test_astype_int_round_trip(self) -> None:
        s = pd.Series([1024, 2048], dtype="bytes")
        assert s.astype("int64").tolist() == [1024, 2048]

    def test_na_handling(self) -> None:
        arr = BytesArray._from_sequence([1024, None])
        assert arr.isna().tolist() == [False, True]


class TestPermsColumn:
    def test_construct_and_display(self) -> None:
        s = pd.Series(["644", "755"], dtype="perms")
        assert isinstance(s[0], Perms)
        assert "rw-r--r--" in repr(s)

    def test_compares_against_literal(self) -> None:
        s = pd.Series(["644", "755"], dtype="perms")
        assert (s == "rw-r--r--").tolist() == [True, False]

    def test_min_max(self) -> None:
        s = pd.Series(["600", "644"], dtype="perms")
        assert s.max() == Perms("644")
        assert isinstance(s.max(), Perms)

    def test_sum_is_refused(self) -> None:
        with pytest.raises(TypeError):
            PermsArray._from_sequence(["644"])._reduce("sum")


class TestPathColumn:
    def test_construct_tidies(self) -> None:
        s = pd.Series(["a//b/", "c"], dtype="path")
        assert s[0] == "a/b"
        assert isinstance(s[0], FsPath)

    def test_truediv_joins(self) -> None:
        s = pd.Series(["a", "b"], dtype="path")
        joined = s / "x.txt"
        assert joined.tolist() == ["a/x.txt", "b/x.txt"]
        assert joined.dtype.name == "path"

    def test_sortable(self) -> None:
        s = pd.Series(["b", "a"], dtype="path")
        assert s.sort_values().tolist() == ["a", "b"]


class TestAccessor:
    def test_path_algebra(self) -> None:
        s = pd.Series(["src/a.py", "docs/b.md"])
        assert s.fs.ext().tolist() == ["py", "md"]
        assert s.fs.dir().tolist() == ["src", "docs"]
        assert s.fs.name().tolist() == ["a.py", "b.md"]
        assert s.fs.with_ext("html").tolist() == ["src/a.html", "docs/b.html"]
        assert s.fs.with_ext("html").dtype.name == "path"

    def test_filesystem_queries(self, base: FsPath) -> None:
        s = pd.Series([str(base / "big.bin"), str(base / "sub"), str(base / "nope")])
        assert s.fs.exists().tolist() == [True, True, False]
        assert s.fs.is_file().tolist() == [True, False, False]
        assert s.fs.is_dir().tolist() == [False, True, False]

    def test_size_column_is_bytes(self, base: FsPath) -> None:
        s = pd.Series([str(base / "big.bin"), str(base / "small.txt")])
        sizes = s.fs.size()
        assert sizes.dtype.name == "bytes"
        assert (sizes > "1K").tolist() == [True, False]

    def test_index_is_preserved(self) -> None:
        s = pd.Series(["a.py", "b.md"], index=["x", "y"])
        assert s.fs.ext().index.tolist() == ["x", "y"]


class TestInfoFrames:
    def test_file_info_is_typed_frame(self, base: FsPath) -> None:
        df = fs.file_info(base / "big.bin")
        assert isinstance(df, pd.DataFrame)
        assert df["path"].dtype.name == "path"
        assert df["size"].dtype.name == "bytes"
        assert df["permissions"].dtype.name == "perms"
        assert str(df["modification_time"].dtype).startswith("datetime64")

    def test_headline_demo(self, base: FsPath) -> None:
        out = (
            fs.dir_info(base, recurse=True)
            .query("size > '1KB' and type == 'file'")
            .sort_values("size", ascending=False)
            .loc[:, ["path", "permissions", "size", "modification_time"]]
        )
        assert len(out) == 1
        assert str(out.iloc[0]["path"]).endswith("big.bin")
        assert isinstance(out.iloc[0]["size"], Bytes)

    def test_empty_dir_info_keeps_schema(self, base: FsPath) -> None:
        df = fs.dir_info(base / "sub")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns[:4]) == ["path", "type", "size", "permissions"]

    def test_groupby_on_dir(self, base: FsPath) -> None:
        df = fs.dir_info(base, recurse=True, type="file")
        df = df.assign(parent=df["path"].astype(str).map(lambda p: fs.path_dir(p)))
        agg = df.groupby("parent")["size"].max()
        assert len(agg) == 1


class TestPathArrayInternals:
    def test_take_with_fill(self) -> None:
        arr = PathArray._from_sequence(["a", "b"])
        taken = arr.take([0, -1], allow_fill=True)
        assert taken[0] == "a"
        assert pd.isna(taken[1])

    def test_concat(self) -> None:
        a = PathArray._from_sequence(["a"])
        b = PathArray._from_sequence(["b"])
        assert PathArray._concat_same_type([a, b]).tolist() == ["a", "b"]
