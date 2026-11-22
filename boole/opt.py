"""Show the path from a Python-like script to a native Boole function."""

from dataclasses import dataclass

from boole import ast as A
from boole.cgen import generate_c
from boole.errors import BooleError


@dataclass
class Note:
    name: str
    status: str
    detail: str


def report(program: A.Program):
    notes = []
    _functions(program.body, "", notes)
    try:
        generate_c(program)
        native = "native: this file compiles with `boole build`"
    except BooleError as err:
        native = "interpreter: " + err.message
    return notes, native


def _functions(stmts, prefix, notes):
    for stmt in stmts:
        if isinstance(stmt, A.FuncDef):
            qual = f"{prefix}{stmt.name}"
            if stmt.is_static:
                notes.append(
                    Note(
                        qual,
                        "static",
                        "types are checked; keep the body in the native subset to compile it",
                    )
                )
            else:
                notes.append(
                    Note(
                        qual,
                        "dynamic",
                        "script function; add static and annotations when you want it checked",
                    )
                )
            _functions(stmt.body, qual + ".", notes)
        elif isinstance(stmt, A.ClassDef):
            _functions(stmt.body, stmt.name + ".", notes)
        elif isinstance(stmt, A.IfStmt):
            _functions(stmt.body, prefix, notes)
            for _cond, body in stmt.elifs:
                _functions(body, prefix, notes)
            if stmt.else_body:
                _functions(stmt.else_body, prefix, notes)
        elif isinstance(stmt, (A.WhileStmt, A.ForStmt)):
            _functions(stmt.body, prefix, notes)
        elif isinstance(stmt, A.TryStmt):
            _functions(stmt.body, prefix, notes)
            for _exc, _as_name, body in stmt.handlers:
                _functions(body, prefix, notes)
            if stmt.final:
                _functions(stmt.final, prefix, notes)
