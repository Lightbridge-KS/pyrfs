"""Bytes and Perms typed scalars."""

import pytest

from pyfs import Bytes, FsValueError, Perms


class TestBytesConstruction:
    def test_from_int(self) -> None:
        assert Bytes(1024) == 1024

    def test_from_str(self) -> None:
        assert Bytes("10MB") == 10 * 1024**2

    def test_is_an_int(self) -> None:
        assert isinstance(Bytes(5), int)
        assert int(Bytes("1K")) == 1024

    def test_invalid_literal(self) -> None:
        with pytest.raises(FsValueError):
            Bytes("ten megs")

    def test_repr_exact_str_human(self) -> None:
        b = Bytes(455200)
        assert repr(b) == "Bytes(455200)"
        assert str(b) == "444.5K"
        assert f"{b}" == "444.5K"
        assert f"{b:d}" == "455200"


class TestBytesComparison:
    def test_vs_string(self) -> None:
        assert Bytes(455200) < "1MB"
        assert Bytes("10MB") > "1MB"
        assert Bytes("1K") == "1KB"
        assert Bytes("2K") >= "2048"
        assert Bytes("1K") != "2K"

    def test_vs_numbers(self) -> None:
        assert Bytes(10) == 10
        assert Bytes(10) < 11
        assert Bytes(10) != 11

    def test_unparseable_string_is_unequal(self) -> None:
        assert Bytes(10) != "not a size"

    def test_sortable(self) -> None:
        sizes = [Bytes("1M"), Bytes("1K"), Bytes("1G")]
        assert sorted(sizes) == [Bytes("1K"), Bytes("1M"), Bytes("1G")]

    def test_hashable(self) -> None:
        assert hash(Bytes(10)) == hash(10)


class TestBytesArithmetic:
    def test_add_stays_bytes(self) -> None:
        total = Bytes("1MB") + Bytes("500KB")
        assert isinstance(total, Bytes)
        assert total == 1024**2 + 500 * 1024

    def test_add_string_rhs(self) -> None:
        assert Bytes("1K") + "1K" == Bytes("2K")

    def test_sum_builtin(self) -> None:
        total = sum([Bytes("1MB"), Bytes("500KB")])
        assert isinstance(total, Bytes)
        assert str(total) == "1.49M"

    def test_sub_mul_floordiv(self) -> None:
        assert Bytes("2K") - "1K" == Bytes("1K")
        assert isinstance(Bytes("1K") * 2, Bytes)
        assert Bytes("1K") * 2 == 2048
        assert 2 * Bytes("1K") == 2048
        assert Bytes("4K") // 2 == Bytes("2K")

    def test_truediv_is_ratio(self) -> None:
        assert Bytes("2K") / Bytes("1K") == 2.0

    def test_neg_abs(self) -> None:
        assert str(-Bytes("2K")) == "-2K"
        assert abs(-Bytes("2K")) == Bytes("2K")

    def test_min_max(self) -> None:
        assert max(Bytes("1K"), Bytes("1M")) == Bytes("1M")


class TestPermsConstruction:
    def test_from_octal_str(self) -> None:
        assert Perms("644") == 0o644

    def test_from_symbolic(self) -> None:
        assert Perms("u+rw,go+r") == 0o644

    def test_from_rwx(self) -> None:
        assert Perms("rwxr-xr-x") == 0o755

    def test_from_int(self) -> None:
        assert Perms(0o600) == 0o600

    def test_is_an_int(self) -> None:
        assert isinstance(Perms("644"), int)

    def test_repr_and_str(self) -> None:
        p = Perms("644")
        assert repr(p) == "Perms('rw-r--r--')"
        assert str(p) == "rw-r--r--"
        assert f"{p}" == "rw-r--r--"

    def test_invalid_literal(self) -> None:
        with pytest.raises(FsValueError):
            Perms("u+q")


class TestPermsAlgebra:
    def test_eq_parses_string(self) -> None:
        assert Perms("644") == "rw-r--r--"
        assert Perms("644") == "u=rw,go=r"
        assert Perms("644") != "777"

    def test_and_or_stay_perms(self) -> None:
        out = Perms("644") | "u+x"
        assert isinstance(out, Perms)
        assert str(out) == "rwxr--r--"
        masked = Perms("644") & "u+r"
        assert isinstance(masked, Perms)
        assert masked == 0o400

    def test_invert(self) -> None:
        assert ~Perms("777") == Perms("000")
        assert ~Perms("644") == 0o133

    def test_xor(self) -> None:
        assert Perms("644") ^ "644" == Perms("000")

    def test_hashable(self) -> None:
        assert hash(Perms("644")) == hash(0o644)
