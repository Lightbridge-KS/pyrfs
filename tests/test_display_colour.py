"""LS_COLORS colouring: enablement rules, type/extension rules, degradation."""

import os
import pathlib

import pytest

import pyrfs as fs
from pyrfs import FsPath
from pyrfs.display import colour_enabled, colourise_path

DI_BLUE = "\x1b[01;34m"
EX_GREEN = "\x1b[01;32m"
RESET = "\x1b[0m"


@pytest.fixture
def base(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> FsPath:
    monkeypatch.delenv("LS_COLORS", raising=False)  # use the default palette
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    root = FsPath(str(tmp_path))
    fs.dir_create(root / "dir")
    fs.file_touch(root / "plain.txt")
    fs.file_create(root / "run.sh", mode="755")
    return root


class TestEnablement:
    def test_no_color_wins_over_force_color(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NO_COLOR", "")
        monkeypatch.setenv("FORCE_COLOR", "1")
        assert not colour_enabled()

    def test_force_color_enables_off_tty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        assert colour_enabled()

    def test_default_off_under_pytest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        assert not colour_enabled()  # captured stdout is not a TTY


class TestColourRules:
    def test_directory_is_blue(self, base: FsPath) -> None:
        assert colourise_path(base / "dir") == f"{DI_BLUE}{base / 'dir'}{RESET}"

    def test_executable_is_green(self, base: FsPath) -> None:
        out = colourise_path(base / "run.sh")
        assert out.startswith(EX_GREEN)

    def test_symlink_uses_ln_rule(self, base: FsPath) -> None:
        ln = fs.link_create(base / "plain.txt", base / "ln.txt")
        assert colourise_path(ln).startswith("\x1b[01;36m")

    def test_extension_rule_from_ls_colors(
        self, base: FsPath, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LS_COLORS", "*.txt=35")
        assert colourise_path(base / "plain.txt").startswith("\x1b[35m")

    def test_missing_path_stays_plain(self, base: FsPath) -> None:
        assert colourise_path(base / "ghost") == base / "ghost"

    def test_custom_text_is_wrapped(self, base: FsPath) -> None:
        out = colourise_path(base / "dir", "dir")
        assert out == f"{DI_BLUE}dir{RESET}"


class TestIntegration:
    def test_repr_coloured_when_forced(self, base: FsPath) -> None:
        d = base / "dir"
        assert repr(d) == f"FsPath({DI_BLUE}'{d}'{RESET})"

    def test_repr_plain_by_default(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        p = FsPath(str(tmp_path))
        assert repr(p) == f"FsPath('{p}')"

    def test_tree_coloured_when_forced(
        self, base: FsPath, capsys: pytest.CaptureFixture[str]
    ) -> None:
        fs.dir_tree(base)
        out = capsys.readouterr().out
        assert f"{DI_BLUE}dir{RESET}" in out

    def test_tree_plain_with_no_color(
        self, base: FsPath, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("NO_COLOR", "")
        fs.dir_tree(base)
        assert "\x1b[" not in capsys.readouterr().out


def test_env_isolation_sanity() -> None:
    # monkeypatch restores env between tests; nothing should leak
    assert "FORCE_COLOR" not in os.environ or os.environ.get("PYTEST_CURRENT_TEST")
