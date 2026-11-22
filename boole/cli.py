"""Command-line interface for Boole."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from boole import __version__
from boole.checker import check
from boole.errors import BooleError
from boole.harness import run_bench, run_tests
from boole.interpreter import interpret
from boole.lexer import lex
from boole.native import build_native, run_native
from boole.opt import report as opt_report
from boole.parser import parse


def _load(path: Path):
    return path.read_text(encoding="utf-8")


def cmd_run(args):
    path = Path(args.file)
    source = _load(path)
    try:
        program = parse(source, str(path))
        do_check = getattr(args, "check", False) or program.static
        if do_check:
            errors = check(program, str(path))
            if errors:
                for err in errors:
                    print(err.format(str(path)), file=sys.stderr)
                return 1
        if args.interp:
            interpret(program, str(path), check_types=do_check)
            return 0
        try:
            return run_native(source, str(path))
        except BooleError as err:
            if "use `boole run --interp`" in err.message or err.kind == "CompileError":
                # fall back for unsupported native features
                if args.strict_native:
                    print(err.format(str(path)), file=sys.stderr)
                    return 1
                print(f"note: native unsupported ({err.message}); using interpreter", file=sys.stderr)
                interpret(program, str(path), check_types=do_check)
                return 0
            raise
    except BooleError as err:
        print(err.format(str(path)), file=sys.stderr)
        return 1


def cmd_build(args):
    path = Path(args.file)
    source = _load(path)
    out = Path(args.output) if args.output else path.with_suffix("")
    try:
        program = parse(source, str(path))
        errors = check(program, str(path))
        if errors:
            for err in errors:
                print(err.format(str(path)), file=sys.stderr)
            return 1
        keep = Path(args.emit_c) if args.emit_c else None
        bin_path = build_native(source, str(path), out_bin=out, keep_c=keep)
        print(bin_path)
        return 0
    except BooleError as err:
        print(err.format(str(path)), file=sys.stderr)
        return 1


def cmd_check(args):
    path = Path(args.file)
    source = _load(path)
    try:
        program = parse(source, str(path))
        errors = check(program, str(path))
        if errors:
            for err in errors:
                print(err.format(str(path)), file=sys.stderr)
            print(f"{len(errors)} type error(s)", file=sys.stderr)
            return 1
        print(f"{path}: ok")
        return 0
    except BooleError as err:
        print(err.format(str(path)), file=sys.stderr)
        return 1


def cmd_parse(args):
    path = Path(args.file)
    source = _load(path)
    try:
        program = parse(source, str(path))
        print(f"# {path} static={program.static} stmts={len(program.body)}")
        for stmt in program.body:
            print(type(stmt).__name__, getattr(stmt, "name", ""), f"@{stmt.line}:{stmt.col}")
        return 0
    except BooleError as err:
        print(err.format(str(path)), file=sys.stderr)
        return 1


def cmd_lex(args):
    path = Path(args.file)
    source = _load(path)
    try:
        for tok in lex(source, str(path)):
            print(f"{tok.line}:{tok.col}\t{tok.kind}\t{tok.value!r}")
        return 0
    except BooleError as err:
        print(err.format(str(path)), file=sys.stderr)
        return 1


def cmd_opt(args):
    path = Path(args.file)
    source = _load(path)
    try:
        program = parse(source, str(path))
        errors = check(program, str(path))
        if errors:
            for err in errors:
                print(err.format(str(path)), file=sys.stderr)
            return 1
        notes, native = opt_report(program)
        print(native)
        if not notes:
            print("no functions")
            return 0
        for note in notes:
            print(f"{note.name}: {note.status} — {note.detail}")
        return 0
    except BooleError as err:
        print(err.format(str(path)), file=sys.stderr)
        return 1


def cmd_test(args):
    directory = Path(args.dir) if args.dir else None
    return run_tests(directory)


def cmd_bench(args):
    directory = Path(args.dir) if args.dir else None
    return run_bench(directory)


def cmd_version(_args):
    print(f"boole {__version__}")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # bare: boole file.boole
    if argv and not argv[0].startswith("-") and argv[0] not in {
        "run", "build", "check", "opt", "test", "bench", "parse", "lex", "version", "help",
    } and argv[0].endswith(".boole"):
        return cmd_run(argparse.Namespace(file=argv[0], check=False, interp=False, strict_native=False))

    parser = argparse.ArgumentParser(prog="boole", description="Boole programming language")
    parser.add_argument("--version", action="store_true", help="print version")
    sub = parser.add_subparsers(dest="cmd")

    p_run = sub.add_parser("run", help="compile to native C and run (default)")
    p_run.add_argument("file")
    p_run.add_argument("--check", action="store_true", help="type-check before run")
    p_run.add_argument("--interp", action="store_true", help="use Python interpreter instead of native")
    p_run.add_argument("--strict-native", action="store_true", help="do not fall back to interpreter")
    p_run.set_defaults(func=cmd_run)

    p_build = sub.add_parser("build", help="emit a native binary via clang -O3 -flto")
    p_build.add_argument("file")
    p_build.add_argument("-o", "--output", help="output binary path")
    p_build.add_argument("--emit-c", help="also write generated C to this path")
    p_build.add_argument("--check", action="store_true")
    p_build.set_defaults(func=cmd_build)

    p_opt = sub.add_parser("opt", help="show which functions are typed and whether the file is native")
    p_opt.add_argument("file")
    p_opt.set_defaults(func=cmd_opt)

    p_test = sub.add_parser("test", help="run tests/programs/*.boole (# expect: lines)")
    p_test.add_argument("--dir", help="test directory")
    p_test.set_defaults(func=cmd_test)

    p_bench = sub.add_parser("bench", help="benchmark vs Python")
    p_bench.add_argument("--dir", help="benchmark directory")
    p_bench.set_defaults(func=cmd_bench)

    p_check = sub.add_parser("check", help="type-check a .boole file")
    p_check.add_argument("file")
    p_check.set_defaults(func=cmd_check)

    p_parse = sub.add_parser("parse", help="dump top-level AST nodes")
    p_parse.add_argument("file")
    p_parse.set_defaults(func=cmd_parse)

    p_lex = sub.add_parser("lex", help="dump tokens")
    p_lex.add_argument("file")
    p_lex.set_defaults(func=cmd_lex)

    p_ver = sub.add_parser("version", help="print version")
    p_ver.set_defaults(func=cmd_version)

    args = parser.parse_args(argv)
    if args.version:
        return cmd_version(args)
    if not args.cmd:
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
