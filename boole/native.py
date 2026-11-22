"""Compile Boole to a native binary via C + clang -O2."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from boole.cgen import generate_c
from boole.errors import BooleError
from boole.parser import parse

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_C = ROOT / "runtime" / "boole_rt.c"
RUNTIME_OOP_C = ROOT / "runtime" / "boole_oop.c"
RUNTIME_H = ROOT / "runtime" / "boole_rt.h"


def build_native(
    source: str,
    path: str,
    out_bin: Path | None = None,
    keep_c: Path | None = None,
    *,
    fast: bool = False,
) -> Path:
    if not RUNTIME_C.exists():
        raise BooleError("CompileError", f"missing runtime {RUNTIME_C}", 1, 1)
    program = parse(source, path)
    c_source = generate_c(program, path=path)

    if keep_c is not None:
        keep_c.write_text(c_source, encoding="utf-8")
        c_file = keep_c
        cleanup = False
    else:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".c", delete=False, encoding="utf-8")
        tmp.write(c_source)
        tmp.close()
        c_file = Path(tmp.name)
        cleanup = True

    if out_bin is None:
        fd, name = tempfile.mkstemp(prefix="boole_", suffix=".bin")
        os.close(fd)
        out_bin = Path(name)

    # Tests use -O1 for speed; production/bench use -O3 -flto.
    opt_flags = ["-O1"] if fast else ["-O3", "-flto"]
    if not RUNTIME_OOP_C.exists():
        raise BooleError("CompileError", f"missing runtime {RUNTIME_OOP_C}", 1, 1)
    cmd = [
        "clang",
        *opt_flags,
        "-std=c11",
        f"-I{RUNTIME_H.parent}",
        str(c_file),
        str(RUNTIME_C),
        str(RUNTIME_OOP_C),
        "-lm",
        "-o",
        str(out_bin),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise BooleError(
                "CompileError",
                "clang failed:\n" + (proc.stderr or proc.stdout or "unknown error"),
                1,
                1,
            )
    finally:
        if cleanup:
            try:
                os.unlink(c_file)
            except OSError:
                pass
    os.chmod(out_bin, 0o755)
    return out_bin


def run_native(source: str, path: str) -> int:
    bin_path = build_native(source, path)
    try:
        proc = subprocess.run([str(bin_path)])
        return proc.returncode
    finally:
        try:
            os.unlink(bin_path)
        except OSError:
            pass
