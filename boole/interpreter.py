"""Boole interpreter — dynamic runtime with optional prior static checks."""

from __future__ import annotations

import sys

from boole import ast as A
from boole.builtins_mod import make_builtins
from boole.errors import BooleError, BreakSignal, ContinueSignal, ReturnSignal
from boole.typesys import from_ast, from_value, consistent


class Function:
    def __init__(self, node: A.FuncDef, env: dict, interp: "Interpreter"):
        self.node = node
        self.env = env
        self.interp = interp

    def __call__(self, *args, **kwargs):
        return self.interp.call_function(self, args, kwargs)

    def __repr__(self):
        return f"<fn {self.node.name}>"


class ClassObj:
    def __init__(self, node: A.ClassDef, env: dict, interp: "Interpreter"):
        self.node = node
        self.name = node.name
        self.env = env
        self.methods = {}
        self.interp = interp
        for item in node.body:
            if isinstance(item, A.FuncDef):
                self.methods[item.name] = Function(item, env, interp)

    def find_method(self, name, seen=None):
        seen = seen or set()
        if id(self) in seen:
            return None
        seen.add(id(self))
        if name in self.methods:
            return self.methods[name]
        base_name = self.node.base
        if not base_name:
            return None
        base = self.env.get(base_name)
        if isinstance(base, ClassObj):
            return base.find_method(name, seen)
        return None

    def __call__(self, *args, **kwargs):
        inst = Instance(self)
        init = self.find_method("__init__")
        if init:
            init(inst, *args, **kwargs)
        elif args or kwargs:
            raise BooleError(
                "TypeError",
                f"{self.name}() takes no arguments",
                self.node.line,
                self.node.col,
            )
        return inst

    def __repr__(self):
        return f"<class {self.name}>"


class Module:
    """A loaded .boole file. Attributes are the names that file defined."""

    def __init__(self, exports):
        object.__setattr__(self, "_exports", exports)

    def __getattr__(self, name):
        exports = object.__getattribute__(self, "_exports")
        if name in exports:
            return exports[name]
        raise AttributeError(name)

    def __repr__(self):
        exports = object.__getattribute__(self, "_exports")
        return f"<module {', '.join(sorted(exports))}>"


class Instance:
    def __init__(self, cls: ClassObj):
        self.cls = cls
        self.fields = {}

    def __getattr__(self, name):
        if name in ("cls", "fields"):
            return object.__getattribute__(self, name)
        fields = object.__getattribute__(self, "fields")
        if name in fields:
            return fields[name]
        cls = object.__getattribute__(self, "cls")
        method = cls.find_method(name)
        if method is not None:

            def bound(*args, **kwargs):
                return method(self, *args, **kwargs)

            return bound
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in ("cls", "fields"):
            object.__setattr__(self, name, value)
            return
        self.fields[name] = value

    def __repr__(self):
        return f"<{self.cls.name} instance>"


class Interpreter:
    def __init__(self, path="<stdin>", stdout=None, check_types=False, modules=None, loading=None):
        self.path = path
        self.stdout = stdout or sys.stdout
        self.check_types = check_types
        self.modules = modules if modules is not None else {}
        self.loading = loading if loading is not None else set()
        self.globals = make_builtins(self)
        self.env = self.globals

    def run(self, program: A.Program):
        marker = self._abs_path()
        if marker:
            self.loading.add(marker)
        try:
            for stmt in program.body:
                self.exec_stmt(stmt)
        finally:
            if marker:
                self.loading.discard(marker)
        return 0

    def _abs_path(self):
        if self.path in ("<stdin>", ""):
            return None
        from pathlib import Path

        return str(Path(self.path).resolve())

    def exec_block(self, body):
        for stmt in body:
            self.exec_stmt(stmt)

    def exec_stmt(self, node):
        if isinstance(node, A.FuncDef):
            # Close over the live environment so a function can call one defined later.
            self.env[node.name] = Function(node, self.env, self)
            return
        if isinstance(node, A.ClassDef):
            self.env[node.name] = ClassObj(node, self.env, self)
            return
        if isinstance(node, A.AnnAssign):
            value = None if node.value is None else self.eval(node.value)
            if self.check_types and node.typ is not None and value is not None:
                expected = from_ast(node.typ)
                got = from_value(value)
                if not consistent(got, expected):
                    raise BooleError(
                        "TypeError",
                        f"cannot assign {got} to {expected}",
                        node.line,
                        node.col,
                    )
            self.assign(node.target, value)
            return
        if isinstance(node, A.Assign):
            value = self.eval(node.value)
            self.assign(node.target, value)
            return
        if isinstance(node, A.AugAssign):
            current = self.eval(node.target)
            right = self.eval(node.value)
            ops = {
                "+": lambda a, b: a + b,
                "-": lambda a, b: a - b,
                "*": lambda a, b: a * b,
                "/": lambda a, b: a / b,
                "//": lambda a, b: a // b,
                "%": lambda a, b: a % b,
                "**": lambda a, b: a**b,
            }
            self.assign(node.target, ops[node.op](current, right))
            return
        if isinstance(node, A.IfStmt):
            if self.eval(node.cond):
                self.exec_block(node.body)
                return
            for cond, body in node.elifs:
                if self.eval(cond):
                    self.exec_block(body)
                    return
            if node.else_body is not None:
                self.exec_block(node.else_body)
            return
        if isinstance(node, A.WhileStmt):
            while self.eval(node.cond):
                try:
                    self.exec_block(node.body)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
            return
        if isinstance(node, A.ForStmt):
            iterable = self.eval(node.iterable)
            for item in iterable:
                self.env[node.name] = item
                try:
                    self.exec_block(node.body)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
            return
        if isinstance(node, A.TryStmt):
            try:
                self.exec_block(node.body)
            except BooleError:
                raise
            except Exception as exc:
                handled = False
                for exc_name, as_name, body in node.handlers:
                    cls = self.env.get(exc_name, Exception)
                    if isinstance(cls, type) and isinstance(exc, cls):
                        if as_name:
                            self.env[as_name] = exc
                        self.exec_block(body)
                        handled = True
                        break
                    if exc_name == "Exception":
                        if as_name:
                            self.env[as_name] = exc
                        self.exec_block(body)
                        handled = True
                        break
                if not handled:
                    raise
            finally:
                if node.final:
                    self.exec_block(node.final)
            return
        if isinstance(node, A.ReturnStmt):
            value = None if node.value is None else self.eval(node.value)
            raise ReturnSignal(value)
        if isinstance(node, A.RaiseStmt):
            cls = self.env.get(node.exc, RuntimeError)
            msg = None if node.message is None else self.eval(node.message)
            if isinstance(cls, type):
                raise cls(msg) if msg is not None else cls()
            raise RuntimeError(msg or node.exc)
        if isinstance(node, A.AssertStmt):
            if not self.eval(node.cond):
                msg = "assertion failed"
                if node.message is not None:
                    msg = str(self.eval(node.message))
                raise AssertionError(msg)
            return
        if isinstance(node, A.ExprStmt):
            self.eval(node.expr)
            return
        if isinstance(node, A.PassStmt):
            return
        if isinstance(node, A.BreakStmt):
            raise BreakSignal()
        if isinstance(node, A.ContinueStmt):
            raise ContinueSignal()
        if isinstance(node, A.ImportStmt):
            self.import_module(node)
            return

    def import_module(self, node):
        import json
        import math
        from pathlib import Path

        name = node.name
        if name == "math":
            self.env["math"] = math
            return
        if name == "json":
            self.env["json"] = json
            return
        if name == "sys":
            self.env["sys"] = sys
            return
        base = Path.cwd() if self.path in ("<stdin>", "") else Path(self.path).resolve().parent
        file_path = base.joinpath(*name.split(".")).with_suffix(".boole")
        if not file_path.is_file():
            raise BooleError(
                "ImportError",
                f"cannot import '{name}'",
                node.line,
                node.col,
            )
        abspath = str(file_path.resolve())
        if abspath in self.loading:
            raise BooleError("ImportError", f"circular import '{name}'", node.line, node.col)
        if abspath not in self.modules:
            from boole.checker import check
            from boole.parser import parse

            program = parse(file_path.read_text(encoding="utf-8"), abspath)
            errors = check(program, abspath)
            if errors:
                raise errors[0]
            child = Interpreter(
                path=abspath,
                stdout=self.stdout,
                check_types=True,
                modules=self.modules,
                loading=self.loading,
            )
            builtin_names = set(child.env)
            child.run(program)
            exports = {key: value for key, value in child.env.items() if key not in builtin_names}
            self.modules[abspath] = Module(exports)
        self._bind_import(name, self.modules[abspath])

    def _bind_import(self, name, module):
        parts = name.split(".")
        if len(parts) == 1:
            self.env[parts[0]] = module
            return
        top = self.env.get(parts[0])
        if not isinstance(top, Module):
            top = Module({})
            self.env[parts[0]] = top
        current = top
        for part in parts[1:-1]:
            exports = object.__getattribute__(current, "_exports")
            nxt = exports.get(part)
            if not isinstance(nxt, Module):
                nxt = Module({})
                exports[part] = nxt
            current = nxt
        object.__getattribute__(current, "_exports")[parts[-1]] = module

    def assign(self, target, value):
        if isinstance(target, A.Name):
            self.env[target.id] = value
            return
        if isinstance(target, A.Index):
            obj = self.eval(target.value)
            index = self.eval(target.index)
            obj[index] = value
            return
        if isinstance(target, A.Attribute):
            obj = self.eval(target.value)
            if isinstance(obj, Instance):
                obj.fields[target.attr] = value
            else:
                setattr(obj, target.attr, value)
            return
        raise BooleError("TypeError", "invalid assignment target", target.line, target.col)

    def call_function(self, fn: Function, args, kwargs):
        node = fn.node
        params = node.params
        if len(args) + len(kwargs) > len(params):
            raise BooleError(
                "TypeError",
                f"{node.name}() takes {len(params)} arguments",
                node.line,
                node.col,
            )
        local = dict(fn.env)
        values = {}
        for i, p in enumerate(params):
            if i < len(args):
                values[p.name] = args[i]
            elif p.name in kwargs:
                values[p.name] = kwargs[p.name]
            elif p.default is not None:
                values[p.name] = self.eval_in(p.default, local)
            else:
                raise BooleError(
                    "TypeError",
                    f"{node.name}() missing argument '{p.name}'",
                    node.line,
                    node.col,
                )
        if self.check_types or node.is_static:
            for p in params:
                if p.typ is not None:
                    expected = from_ast(p.typ)
                    got = from_value(values[p.name])
                    if not consistent(got, expected):
                        raise BooleError(
                            "TypeError",
                            f"parameter '{p.name}': {got} not consistent with {expected}",
                            p.line,
                            p.col,
                        )
        local.update(values)
        saved = self.env
        self.env = local
        try:
            self.exec_block(node.body)
            result = None
        except ReturnSignal as ret:
            result = ret.value
        finally:
            self.env = saved
        if (self.check_types or node.is_static) and node.returns is not None:
            expected = from_ast(node.returns)
            got = from_value(result)
            if not consistent(got, expected):
                raise BooleError(
                    "TypeError",
                    f"return {got} not consistent with {expected}",
                    node.line,
                    node.col,
                )
        return result

    def eval_in(self, node, env):
        saved = self.env
        self.env = env
        try:
            return self.eval(node)
        finally:
            self.env = saved

    def eval(self, node):
        if isinstance(node, A.Literal):
            return node.value
        if isinstance(node, A.Name):
            if node.id not in self.env:
                raise BooleError("NameError", f"name '{node.id}' is not defined", node.line, node.col)
            return self.env[node.id]
        if isinstance(node, A.ListLit):
            return [self.eval(e) for e in node.elts]
        if isinstance(node, A.DictLit):
            return {self.eval(k): self.eval(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, A.FString):
            out = []
            for part in node.parts:
                if part[0] == "text":
                    out.append(part[1])
                else:
                    out.append(str(self.eval(part[1])))
            return "".join(out)
        if isinstance(node, A.Unary):
            v = self.eval(node.operand)
            if node.op == "not":
                return not v
            if node.op == "+":
                return +v
            if node.op == "-":
                return -v
        if isinstance(node, A.Binary):
            left = self.eval(node.left)
            right = self.eval(node.right)
            ops = {
                "+": lambda a, b: a + b,
                "-": lambda a, b: a - b,
                "*": lambda a, b: a * b,
                "/": lambda a, b: a / b,
                "//": lambda a, b: a // b,
                "%": lambda a, b: a % b,
                "**": lambda a, b: a**b,
            }
            try:
                return ops[node.op](left, right)
            except (ZeroDivisionError, OverflowError, ValueError, TypeError):
                # Let try/except in Boole catch these as normal exceptions.
                raise
            except Exception as exc:
                raise BooleError("TypeError", str(exc), node.line, node.col) from exc
        if isinstance(node, A.BoolOp):
            left = self.eval(node.left)
            if node.op == "and":
                return left and self.eval(node.right)
            return left or self.eval(node.right)
        if isinstance(node, A.Compare):
            left = self.eval(node.left)
            for op, comp_node in zip(node.ops, node.comparators):
                right = self.eval(comp_node)
                if op == "==":
                    ok = left == right
                elif op == "!=":
                    ok = left != right
                elif op == "<":
                    ok = left < right
                elif op == ">":
                    ok = left > right
                elif op == "<=":
                    ok = left <= right
                elif op == ">=":
                    ok = left >= right
                elif op == "in":
                    ok = left in right
                elif op == "not in":
                    ok = left not in right
                elif op == "is":
                    ok = left is right
                elif op == "is not":
                    ok = left is not right
                else:
                    raise BooleError("RuntimeError", f"bad compare {op}", node.line, node.col)
                if not ok:
                    return False
                left = right
            return True
        if isinstance(node, A.Ternary):
            return self.eval(node.body) if self.eval(node.cond) else self.eval(node.orelse)
        if isinstance(node, A.Call):
            func = self.eval(node.func)
            args = [self.eval(a) for a in node.args]
            kwargs = {kw.name: self.eval(kw.value) for kw in node.keywords}
            try:
                return func(*args, **kwargs)
            except BooleError:
                raise
            except Exception as exc:
                raise BooleError("RuntimeError", str(exc), node.line, node.col) from exc
        if isinstance(node, A.Index):
            obj = self.eval(node.value)
            index = self.eval(node.index)
            try:
                return obj[index]
            except Exception as exc:
                raise BooleError("RuntimeError", str(exc), node.line, node.col) from exc
        if isinstance(node, A.Slice):
            obj = self.eval(node.value)
            start = None if node.start is None else self.eval(node.start)
            stop = None if node.stop is None else self.eval(node.stop)
            return obj[start:stop]
        if isinstance(node, A.Attribute):
            obj = self.eval(node.value)
            try:
                if isinstance(obj, Instance):
                    return obj.__getattr__(node.attr)
                return getattr(obj, node.attr)
            except Exception as exc:
                raise BooleError("AttributeError", str(exc), node.line, node.col) from exc
        raise BooleError("RuntimeError", f"cannot evaluate {type(node).__name__}", 1, 1)


def interpret(program, path="<stdin>", stdout=None, check_types=False):
    return Interpreter(path, stdout=stdout, check_types=check_types).run(program)
