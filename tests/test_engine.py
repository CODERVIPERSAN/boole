"""Unit tests for the AI execution engine contract."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest import mock

import pytest

from boole.engine import Capabilities, Task, discover, execute, select

ROOT = Path(__file__).resolve().parents[1]
HELLO = ROOT / "examples" / "hello.boole"


def test_discover_reports_host():
    caps = discover()
    assert caps.interpreter is True
    assert caps.arch
    assert caps.system
    # Runtime files ship in-repo
    assert caps.runtime is True


def test_select_boole_chooses_native_when_clang_present():
    caps = Capabilities(
        clang=True,
        runtime=True,
        interpreter=True,
        assembler=True,
        arch="x86_64",
        system="Linux",
    )
    task = Task(language="boole", source='print("hi")\n', path="x.boole")
    sel = select(task, caps)
    assert sel.backend == "boole_native"
    assert "clang" in sel.reason.lower() or "runtime" in sel.reason.lower()


def test_select_boole_falls_to_interp_without_clang():
    caps = Capabilities(
        clang=False,
        runtime=True,
        interpreter=True,
        assembler=False,
        arch="x86_64",
        system="Linux",
    )
    task = Task(language="boole", source='print("hi")\n')
    sel = select(task, caps)
    assert sel.backend == "boole_interp"


def test_select_non_boole_is_no_backend_without_clang():
    """Foreign languages must not select a native path (clang never consulted for work)."""
    caps = Capabilities(
        clang=True,
        runtime=True,
        interpreter=True,
        assembler=True,
        arch="x86_64",
        system="Linux",
    )
    task = Task(language="python", source="print(1)\n", path="x.py")
    with mock.patch("boole.engine.build_native") as build:
        with mock.patch("boole.engine.run_native") as run:
            sel = select(task, caps)
            result = execute(task, caps=caps)
    assert sel.backend == "no_backend"
    assert result.selection.backend == "no_backend"
    assert result.verification.ok is False
    build.assert_not_called()
    run.assert_not_called()


def test_select_natural_language_is_no_backend():
    caps = discover()
    task = Task(language="nl", source="print hello on the screen")
    sel = select(task, caps)
    assert sel.backend == "no_backend"
    assert "planned" in sel.reason.lower() or "no backend" in sel.reason.lower()


@pytest.mark.skipif(shutil.which("clang") is None, reason="clang required for native path")
def test_execute_boole_hello_native():
    task = Task.from_boole_file(HELLO, mode="run")
    assert select(task).backend == "boole_native"
    with mock.patch("boole.engine.run_native", return_value=0) as run:
        result = execute(task)
    assert result.verification.ok is True
    assert result.selection.backend == "boole_native"
    assert result.exit_code == 0
    run.assert_called_once()


def test_execute_non_boole_never_calls_clang_subprocess():
    task = Task(language="c", source="int main(){return 0;}", path="x.c")
    with mock.patch("subprocess.run") as sub_run:
        with mock.patch("boole.engine.build_native") as build:
            with mock.patch("boole.engine.run_native") as run:
                result = execute(task)
    assert result.selection.backend == "no_backend"
    build.assert_not_called()
    run.assert_not_called()
    sub_run.assert_not_called()
