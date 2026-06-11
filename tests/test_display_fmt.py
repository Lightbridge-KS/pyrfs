"""Byte and permission parse/format round-trips in display.py."""

import pytest

from pyfs import FsValueError
from pyfs.display import humanize_bytes, parse_bytes, parse_perms, perms_to_str


class TestHumanizeBytes:
    @pytest.mark.parametrize(
        ("n", "expected"),
        [
            (0, "0B"),
            (1, "1B"),
            (455, "455B"),
            (1023, "1023B"),
            (1024, "1K"),
            (455200, "444.5K"),
            (10 * 1024**2, "10M"),
            (int(1.5 * 1024**3), "1.5G"),
            (1024**4, "1T"),
            (-2048, "-2K"),
        ],
    )
    def test_format(self, n: int, expected: str) -> None:
        assert humanize_bytes(n) == expected


class TestParseBytes:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("455", 455),
            ("1K", 1024),
            ("1KB", 1024),
            ("1KiB", 1024),
            ("1kb", 1024),
            ("10MB", 10 * 1024**2),
            ("1.5GiB", int(1.5 * 1024**3)),
            ("0B", 0),
            ("445.2K", round(445.2 * 1024)),
        ],
    )
    def test_parse(self, text: str, expected: int) -> None:
        assert parse_bytes(text) == expected

    def test_round_trip(self) -> None:
        for n in [0, 1, 1024, 10 * 1024**2]:
            assert parse_bytes(humanize_bytes(n)) == n

    @pytest.mark.parametrize("bad", ["", "abc", "10XB", "1.2.3K", "MB"])
    def test_invalid_raises(self, bad: str) -> None:
        with pytest.raises(FsValueError):
            parse_bytes(bad)


class TestPermsToStr:
    @pytest.mark.parametrize(
        ("mode", "expected"),
        [
            (0o644, "rw-r--r--"),
            (0o755, "rwxr-xr-x"),
            (0o777, "rwxrwxrwx"),
            (0o000, "---------"),
            (0o600, "rw-------"),
        ],
    )
    def test_format(self, mode: int, expected: str) -> None:
        assert perms_to_str(mode) == expected


class TestParsePerms:
    def test_octal(self) -> None:
        assert parse_perms("644") == 0o644
        assert parse_perms("0755") == 0o755

    def test_int_passthrough(self) -> None:
        assert parse_perms(0o644) == 0o644

    def test_rwx_string(self) -> None:
        assert parse_perms("rw-r--r--") == 0o644
        assert parse_perms("rwxrwxrwx") == 0o777

    def test_symbolic_plus(self) -> None:
        assert parse_perms("u+rw,go+r") == 0o644
        assert parse_perms("u+rwx") == 0o700

    def test_symbolic_all(self) -> None:
        assert parse_perms("a+r") == 0o444
        assert parse_perms("+r") == 0o444

    def test_symbolic_equals_and_minus(self) -> None:
        assert parse_perms("u=rwx,go=rx") == 0o755
        assert parse_perms("a+rwx,go-w") == 0o755

    def test_round_trip_via_rwx(self) -> None:
        for mode in [0o644, 0o755, 0o600, 0o777]:
            assert parse_perms(perms_to_str(mode)) == mode

    @pytest.mark.parametrize("bad", ["", "u+q", "z+r", "rw-r--r-", "abc"])
    def test_invalid_raises(self, bad: str) -> None:
        with pytest.raises(FsValueError):
            parse_perms(bad)
