"""Test and benchmark harness for Boole programs."""

from __future__ import annotations

import io
import re
import subprocess
import sys
import time
from pathlib import Path

from boole.checker import check
from boole.errors import BooleError
from boole.interpreter import interpret
from boole.native import build_native
from boole.parser import parse

ROOT = Path(__file__).resolve().parents[1]
EXPECT_RE = re.compile(r"^#\s*expect:\s*(.*)$")


def parse_expect(source: str) -> list[str]:
    lines = []
    for line in source.splitlines():
        m = EXPECT_RE.match(line.strip())
        if m:
            lines.append(m.group(1))
    return lines


def run_program(path: Path, prefer_native: bool = True) -> tuple[str, str]:
    """Return (stdout, mode) where mode is 'native' or 'interp'."""
    source = path.read_text(encoding="utf-8")
    program = parse(source, str(path))
    errors = check(program, str(path))
    if errors and program.static:
        raise errors[0]

    if prefer_native:
        try:
            bin_path = build_native(source, str(path), fast=True)
            try:
                proc = subprocess.run(
                    [str(bin_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if proc.returncode != 0:
                    raise BooleError(
                        "RuntimeError",
                        proc.stderr.strip() or f"exit {proc.returncode}",
                        1,
                        1,
                    )
                return proc.stdout, "native"
            finally:
                try:
                    bin_path.unlink()
                except OSError:
                    pass
        except BooleError as err:
            if err.kind != "CompileError":
                raise

    buf = io.StringIO()
    interpret(program, str(path), stdout=buf, check_types=program.static)
    return buf.getvalue(), "interp"


def run_tests(directory: Path | None = None) -> int:
    directory = directory or (ROOT / "tests" / "programs")
    files = sorted(directory.glob("*.boole"))
    if not files:
        print(f"no tests in {directory}", file=sys.stderr)
        return 1
    passed = failed = 0
    for path in files:
        source = path.read_text(encoding="utf-8")
        expect = parse_expect(source)
        if not expect:
            print(f"FAIL {path.name}: missing # expect:")
            failed += 1
            continue
        try:
            out, mode = run_program(path)
            got = out.splitlines()
            if got != expect:
                print(f"FAIL {path.name} [{mode}]")
                print(f"  expect: {expect!r}")
                print(f"  got:    {got!r}")
                failed += 1
            else:
                print(f"ok   {path.name} [{mode}]")
                passed += 1
        except Exception as exc:  # noqa: BLE001 — harness reports any failure
            print(f"FAIL {path.name}: {exc}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    return 0 if failed == 0 else 1


def _time_binary(bin_path: Path, runs: int = 3) -> float:
    best = None
    for _ in range(runs):
        t0 = time.perf_counter()
        subprocess.run([str(bin_path)], capture_output=True, text=True, check=True)
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best


def _time_python(code: str, runs: int = 3) -> float:
    best = None
    for _ in range(runs):
        t0 = time.perf_counter()
        subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best


BENCHMARKS = [
    (
        "sum_loop",
        "benchmarks/sum_loop.boole",
        "total=0\nn=0\nwhile n < 5000000:\n    total += n\n    n += 1\nprint(total)",
    ),
    (
        "range_sum",
        "benchmarks/range_sum.boole",
        "total=0\nfor n in range(5000000):\n    total += n\nprint(total)",
    ),
    (
        "fib",
        "benchmarks/fib.boole",
        "def fib(n):\n"
        "    a=0\n"
        "    b=1\n"
        "    i=0\n"
        "    while i<n:\n"
        "        t=a+b\n"
        "        a=b\n"
        "        b=t\n"
        "        i+=1\n"
        "    return a\n"
        "print(fib(40))",
    ),
]


def run_bench(directory: Path | None = None) -> int:
    directory = directory or (ROOT / "benchmarks")
    directory.mkdir(exist_ok=True)
    print(f"{'bench':<12} {'boole_ms':>10} {'python_ms':>10} {'speedup':>10}")
    for name, rel, py_code in BENCHMARKS:
        path = ROOT / rel
        if not path.exists():
            print(f"{name:<12} MISSING {path}")
            continue
        source = path.read_text(encoding="utf-8")
        t_compile = time.perf_counter()
        bin_path = build_native(source, str(path), out_bin=directory / f"{name}.bin")
        compile_s = time.perf_counter() - t_compile
        boole_s = _time_binary(bin_path)
        python_s = _time_python(py_code)
        speedup = python_s / boole_s if boole_s > 0 else float("inf")
        print(
            f"{name:<12} {boole_s*1000:10.2f} {python_s*1000:10.2f} {speedup:9.1f}x"
            f"  (compile {compile_s*1000:.0f}ms)"
        )
    print("\nNotes: times are best-of-3 process runs of already-built binaries.")
    print("If a bench loses: keep ints unboxed, specialize range-for, avoid boxing in hot loops.")
    return 0
