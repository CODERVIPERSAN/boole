"""AI execution engine — capability probe + backend selector for Boole.

Contracts to the existing compiler (`build_native` / `run_native` / interpreter).
Natural-language → asm and other languages are documented targets, not implemented here.
"""

from __future__ import annotations

import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from boole.checker import check
from boole.errors import BooleError
from boole.interpreter import interpret
from boole.native import RUNTIME_C, RUNTIME_OOP_C, build_native, run_native
from boole.parser import parse

BackendName = Literal["boole_native", "boole_interp", "no_backend"]
TaskMode = Literal["run", "binary"]


@dataclass
class Task:
    """Unit of work for the execution engine."""

    language: str
    source: str
    path: str | None = None
    mode: TaskMode = "run"
    check: bool = False
    strict_native: bool = False

    @classmethod
    def from_boole_file(cls, path: Path | str, *, mode: TaskMode = "run", check: bool = False) -> Task:
        p = Path(path)
        return cls(
            language="boole",
            source=p.read_text(encoding="utf-8"),
            path=str(p),
            mode=mode,
            check=check,
        )


@dataclass
class Capabilities:
    clang: bool
    runtime: bool
    interpreter: bool
    assembler: bool
    arch: str
    system: str

    @property
    def can_boole_native(self) -> bool:
        return self.clang and self.runtime


@dataclass
class Selection:
    backend: BackendName
    reason: str
    capabilities: Capabilities


@dataclass
class VerificationRecord:
    ok: bool
    backend: BackendName
    notes: list[str] = field(default_factory=list)


@dataclass
class EngineResult:
    selection: Selection
    verification: VerificationRecord
    exit_code: int | None = None
    binary_path: str | None = None


def discover() -> Capabilities:
    """Probe host tools needed for the first backends."""
    runtime_ok = RUNTIME_C.exists() and RUNTIME_OOP_C.exists()
    return Capabilities(
        clang=shutil.which("clang") is not None,
        runtime=runtime_ok,
        interpreter=True,
        assembler=shutil.which("as") is not None or shutil.which("clang") is not None,
        arch=platform.machine() or "unknown",
        system=platform.system() or "unknown",
    )


def _is_boole_task(task: Task) -> bool:
    lang = (task.language or "").strip().lower()
    if lang in {"boole", "boo", ".boole"}:
        return True
    if task.path and str(task.path).endswith(".boole"):
        return True
    return False


def select(task: Task, caps: Capabilities | None = None) -> Selection:
    """Choose a backend. Never invokes clang or an assembler."""
    caps = caps if caps is not None else discover()

    if not _is_boole_task(task):
        return Selection(
            backend="no_backend",
            reason=f"no backend for language {task.language!r} (NL→asm and foreign languages are planned)",
            capabilities=caps,
        )

    if caps.can_boole_native:
        return Selection(
            backend="boole_native",
            reason="Boole source; clang and runtime available",
            capabilities=caps,
        )

    if caps.interpreter:
        return Selection(
            backend="boole_interp",
            reason="Boole source; native unavailable, using interpreter",
            capabilities=caps,
        )

    return Selection(
        backend="no_backend",
        reason="Boole source but neither clang/runtime nor interpreter available",
        capabilities=caps,
    )


def _verify_boole(task: Task) -> tuple[VerificationRecord, object | None]:
    path = task.path or "<task>"
    notes: list[str] = []
    try:
        program = parse(task.source, path)
    except BooleError as err:
        return VerificationRecord(ok=False, backend="no_backend", notes=[err.format(path)]), None

    do_check = task.check or program.static
    if do_check:
        errors = check(program, path)
        if errors:
            notes.extend(e.format(path) for e in errors)
            return VerificationRecord(ok=False, backend="no_backend", notes=notes), None
        notes.append("typecheck ok")
    else:
        notes.append("typecheck skipped")
    return VerificationRecord(ok=True, backend="boole_native", notes=notes), program


def execute(task: Task, *, caps: Capabilities | None = None) -> EngineResult:
    """Run or build according to selector policy. Non-Boole never calls clang."""
    selection = select(task, caps)
    if selection.backend == "no_backend":
        return EngineResult(
            selection=selection,
            verification=VerificationRecord(
                ok=False,
                backend="no_backend",
                notes=[selection.reason],
            ),
        )

    path = task.path or "<task>"
    verification, program = _verify_boole(task)
    if not verification.ok:
        verification.backend = selection.backend
        return EngineResult(selection=selection, verification=verification)

    assert program is not None

    if selection.backend == "boole_interp":
        interpret(program, path, check_types=False)
        verification.backend = "boole_interp"
        verification.notes.append("executed via interpreter")
        return EngineResult(selection=selection, verification=verification, exit_code=0)

    # boole_native
    try:
        if task.mode == "binary":
            out = build_native(task.source, path)
            verification.backend = "boole_native"
            verification.notes.append(f"binary {out}")
            return EngineResult(
                selection=selection,
                verification=verification,
                exit_code=0,
                binary_path=str(out),
            )
        code = run_native(task.source, path)
        verification.backend = "boole_native"
        verification.notes.append("executed via native")
        return EngineResult(selection=selection, verification=verification, exit_code=code)
    except BooleError as err:
        fallback = (
            "use `boole run --interp`" in err.message or err.kind == "CompileError"
        )
        if task.strict_native or not fallback or not selection.capabilities.interpreter:
            verification.ok = False
            verification.notes.append(err.format(path))
            return EngineResult(selection=selection, verification=verification, exit_code=1)

        # Same policy as cmd_run: fall back to interpreter
        interpret(program, path, check_types=False)
        verification.backend = "boole_interp"
        verification.notes.append(f"native unsupported ({err.message}); using interpreter")
        # Reflect effective backend in selection copy
        selection = Selection(
            backend="boole_interp",
            reason=verification.notes[-1],
            capabilities=selection.capabilities,
        )
        return EngineResult(selection=selection, verification=verification, exit_code=0)
