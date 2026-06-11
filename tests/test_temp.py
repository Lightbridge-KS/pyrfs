"""file_temp and the deterministic push/pop stack."""

import pyfs as fs
from pyfs import FsPath


class TestFileTemp:
    def test_returns_fspath_under_tmpdir(self) -> None:
        p = fs.file_temp()
        assert isinstance(p, FsPath)
        assert p.has_parent(fs.path_temp())

    def test_does_not_create_the_file(self) -> None:
        assert not fs.file_exists(fs.file_temp())

    def test_unique_names(self) -> None:
        assert fs.file_temp() != fs.file_temp()

    def test_pattern_and_ext(self) -> None:
        p = fs.file_temp(pattern="report", ext="csv")
        assert p.name().startswith("report")
        assert p.ext() == "csv"

    def test_ext_with_dot(self) -> None:
        assert fs.file_temp(ext=".csv").ext() == "csv"

    def test_custom_tmp_dir(self) -> None:
        p = fs.file_temp(tmp_dir="scratch")
        assert p.dir() == "scratch"


class TestTempStack:
    def test_push_makes_file_temp_deterministic(self) -> None:
        fs.file_temp_push(["/tmp/one", "/tmp/two"])
        assert fs.file_temp() == "/tmp/one"
        assert fs.file_temp() == "/tmp/two"
        assert fs.file_temp() != "/tmp/one"  # stack drained -> random again

    def test_pop_removes_in_fifo_order(self) -> None:
        fs.file_temp_push("/tmp/a")
        fs.file_temp_push("/tmp/b")
        assert fs.file_temp_pop() == "/tmp/a"
        assert fs.file_temp_pop() == "/tmp/b"
        assert fs.file_temp_pop() is None
