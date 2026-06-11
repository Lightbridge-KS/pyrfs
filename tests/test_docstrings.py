"""Executable docstring examples — every Examples block must actually run.

``pytest --doctest-modules`` cannot see docstrings on ``Vectorized``
instances (they are neither functions nor classes, so doctest's finder
skips them), so this module collects doctests manually from every core
pyrfs module. Each doctest runs with cwd set to a fresh tmp_path, so
examples may create real files; colour is disabled for stable reprs.
"""

from __future__ import annotations

import doctest
import pathlib

import pytest

from pyrfs import display, errors, fspath, info, values
from pyrfs._engine import (
    dirops,
    entry_types,
    fileops,
    ids,
    linkops,
    paths,
    predicates,
    temp,
    vectorize,
)
from pyrfs._engine.vectorize import Vectorized

MODULES = [
    display,
    errors,
    fspath,
    info,
    values,
    dirops,
    entry_types,
    fileops,
    ids,
    linkops,
    paths,
    predicates,
    temp,
    vectorize,
]

OPTIONFLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE


def _collect() -> list[doctest.DocTest]:
    finder = doctest.DocTestFinder(exclude_empty=True)
    parser = doctest.DocTestParser()
    tests: list[doctest.DocTest] = []
    for mod in MODULES:
        tests.extend(t for t in finder.find(mod) if t.examples)
        for name, obj in vars(mod).items():  # Vectorized instances, missed above
            if isinstance(obj, Vectorized) and obj.__doc__:
                t = parser.get_doctest(
                    obj.__doc__, dict(vars(mod)), f"{mod.__name__}.{name}", mod.__file__, 0
                )
                if t.examples:
                    tests.append(t)
    return tests


@pytest.mark.parametrize("dt", _collect(), ids=lambda t: t.name)
def test_docstring_examples(
    dt: doctest.DocTest, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    monkeypatch.setenv("NO_COLOR", "1")  # stable, uncoloured reprs
    monkeypatch.chdir(tmp_path)  # examples may create files — never in the repo
    runner = doctest.DocTestRunner(optionflags=OPTIONFLAGS)
    result = runner.run(dt)
    assert result.failed == 0, f"doctest failed in {dt.name}"
