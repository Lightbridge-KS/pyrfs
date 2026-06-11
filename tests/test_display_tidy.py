"""Tidy-path normalization edge cases."""

import pytest

from pyfs.display import tidy


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("a//b", "a/b"),
        ("a/b/", "a/b"),
        ("a///b////c", "a/b/c"),
        ("/", "/"),
        ("//", "/"),
        ("///", "/"),
        ("a\\b\\c", "a/b/c"),
        ("C:\\data\\x", "C:/data/x"),
        ("C:\\", "C:/"),
        ("C:/", "C:/"),
        ("~/a/", "~/a"),
        ("", ""),
        ("a", "a"),
        ("/a/b/", "/a/b"),
        ("src//a.txt", "src/a.txt"),
    ],
)
def test_tidy(raw: str, expected: str) -> None:
    assert tidy(raw) == expected


def test_tidy_accepts_pathlike(tmp_path: object) -> None:
    import pathlib

    assert tidy(pathlib.PurePosixPath("a/b")) == "a/b"
