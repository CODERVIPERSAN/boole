"""Gradual static checker for Boole.

Unannotated code is Any. Annotated parameters, returns, and bindings are checked.
Module directive `# boole: static` or `static def` requires annotations on that surface.
"""

from boole import ast as A
from boole import typesys as T
from boole.errors import BooleError


class Checker:
    def __init__(self, path="<stdin>"):
        self.path = path
        self.errors = []
        self.env = {}
        self._return = T.ANY
        self._static_fn = False
        self._push_builtins()

    def _push_builtins(self):
        self.env.update(
            {
                "print": T.FuncType([T.ANY], T.NONE),
                "len": T.FuncType([T.ANY], T.INT),
                "range": T.FuncType([T.INT], T.ListType(T.INT)),
                "str": T.FuncType([T.ANY], T.STR),
                "int": T.FuncType([T.ANY], T.INT),
                "float": T.FuncType([T.ANY], T.FLOAT),
                "bool": T.FuncType([T.ANY], T.BOOL),
                "list": T.FuncType([T.ANY], T.ListType(T.ANY)),
                "dict": T.FuncType([], T.DictType(T.ANY, T.ANY)),
                "type": T.FuncType([T.ANY], T.STR),
                "isinstance": T.FuncType([T.ANY, T.ANY], T.BOOL),
                "abs": T.FuncType([T.INT], T.INT),
                "min": T.FuncType([T.ANY], T.ANY),
                "max": T.FuncType([T.ANY], T.ANY),
                "sum": T.FuncType([T.ANY], T.INT),
                "sorted": T.FuncType([T.ANY], T.ListType(T.ANY)),
                "enumerate": T.FuncType([T.ANY], T.ANY),
                "zip": T.FuncType([T.ANY], T.ANY),
                "open": T.FuncType([T.STR], T.ANY),
                "input": T.FuncType([], T.STR),
                "Exception": T.ANY,
                "ValueError": T.ANY,
                "TypeError": T.ANY,
                "RuntimeError": T.ANY,
                "KeyError": T.ANY,
                "IndexError": T.ANY,
                "AssertionError": T.ANY,
            }
        )

    def err(self, node, message):
        line = getattr(node, "line", 1)
        col = getattr(node, "col", 1)
        self.errors.append(BooleError("TypeError", message, line, col))

    def check(self, program: A.Program):
        for stmt in program.body:
            self.stmt(stmt, require=program.static)
        return self.errors

    def stmt(self, node, require=False):
        if isinstance(node, A.FuncDef):
            self.func(node)
            return
        if isinstance(node, A.ClassDef):
            self.env[node.name] = T.Prim(node.name)
            for item in node.body:
                self.stmt(item, require=require)
            return
        if isinstance(node, A.AnnAssign):
            expected = T.from_ast(node.typ)
            if node.value is not None:
                got = self.expr(node.value)
                if not T.consistent(got, expected):
                    self.err(node, f"cannot assign {got} to {expected}")
            if isinstance(node.target, A.Name):
                self.env[node.target.id] = expected
            return
        if isinstance(node, A.Assign):
            got = self.expr(node.value)
            if isinstance(node.target, A.Name):
                existing = self.env.get(node.target.id)
                if require and existing is None:
                    self.err(node, f"unannotated assignment in static context: {node.target.id}")
                    self.env[node.target.id] = got
                    return
                if (
                    existing is not None
                    and not isinstance(existing, T.AnyType)
                    and not T.consistent(got, existing)
                ):
                    if require:
                        self.err(node, f"cannot assign {got} to {existing}")
                    else:
                        # A script may reuse a name. The static type becomes Any.
                        self.env[node.target.id] = T.ANY
                    return
                if existing is None:
                    self.env[node.target.id] = got
            else:
                self.expr(node.target)
            return
        if isinstance(node, A.AugAssign):
            left = self.expr(node.target)
            right = self.expr(node.value)
            if not T.consistent(left, right) and not isinstance(left, T.AnyType):
                self.err(node, f"augmented assign {left} {node.op}= {right}")
            return
        if isinstance(node, A.IfStmt):
            self.expr(node.cond)
            for s in node.body:
                self.stmt(s, require=require)
            for cond, body in node.elifs:
                self.expr(cond)
                for s in body:
                    self.stmt(s, require=require)
            if node.else_body:
                for s in node.else_body:
                    self.stmt(s, require=require)
            return
        if isinstance(node, (A.WhileStmt,)):
            self.expr(node.cond)
            for s in node.body:
                self.stmt(s, require=require)
            return
        if isinstance(node, A.ForStmt):
            self.expr(node.iterable)
            self.env[node.name] = T.ANY
            for s in node.body:
                self.stmt(s, require=require)
            return
        if isinstance(node, A.TryStmt):
            for s in node.body:
                self.stmt(s, require=require)
            for _exc, as_name, body in node.handlers:
                if as_name:
                    self.env[as_name] = T.ANY
                for s in body:
                    self.stmt(s, require=require)
            if node.final:
                for s in node.final:
                    self.stmt(s, require=require)
            return
        if isinstance(node, A.ReturnStmt):
            got = T.NONE if node.value is None else self.expr(node.value)
            if self._static_fn and not T.consistent(got, self._return):
                self.err(node, f"return {got} not consistent with {self._return}")
            return
        if isinstance(node, A.RaiseStmt):
            if node.message is not None:
                self.expr(node.message)
            return
        if isinstance(node, A.AssertStmt):
            self.expr(node.cond)
            if node.message is not None:
                self.expr(node.message)
            return
        if isinstance(node, A.ExprStmt):
            self.expr(node.expr)
            return
        if isinstance(node, (A.PassStmt, A.BreakStmt, A.ContinueStmt, A.ImportStmt)):
            return

    def func(self, node: A.FuncDef):
        params = []
        local = dict(self.env)
        for p in node.params:
            pt = T.from_ast(p.typ) if p.typ else T.ANY
            if node.is_static and p.typ is None:
                self.err(p, f"static function '{node.name}' parameter '{p.name}' needs a type")
            params.append(pt)
            local[p.name] = pt
            if p.default is not None:
                old = self.env
                self.env = local
                got = self.expr(p.default)
                self.env = old
                if not T.consistent(got, pt):
                    self.err(p, f"default {got} not consistent with {pt}")
        ret = T.from_ast(node.returns) if node.returns else T.ANY
        if node.is_static and node.returns is None:
            self.err(node, f"static function '{node.name}' needs a return type")
        self.env[node.name] = T.FuncType(params, ret)
        saved = self.env
        prev_ret, prev_static = self._return, self._static_fn
        self.env = local
        self.env[node.name] = T.FuncType(params, ret)
        self._return = ret
        self._static_fn = node.is_static
        for s in node.body:
            self.stmt(s, require=node.is_static)
        self._return, self._static_fn = prev_ret, prev_static
        self.env = saved
        self.env[node.name] = T.FuncType(params, ret)

    def expr(self, node):
        if node is None:
            return T.NONE
        if isinstance(node, A.Literal):
            return T.from_value(node.value)
        if isinstance(node, A.Name):
            if node.id not in self.env:
                # dynamic: unknown names are Any until runtime
                return T.ANY
            return self.env[node.id]
        if isinstance(node, A.ListLit):
            if not node.elts:
                return T.ListType(T.ANY)
            item = self.expr(node.elts[0])
            for e in node.elts[1:]:
                t = self.expr(e)
                if not T.consistent(item, t):
                    item = T.ANY
            return T.ListType(item)
        if isinstance(node, A.DictLit):
            if not node.keys:
                return T.DictType(T.ANY, T.ANY)
            return T.DictType(self.expr(node.keys[0]), self.expr(node.values[0]))
        if isinstance(node, A.FString):
            for part in node.parts:
                if part[0] == "expr":
                    self.expr(part[1])
            return T.STR
        if isinstance(node, A.Unary):
            t = self.expr(node.operand)
            if node.op == "not":
                return T.BOOL
            return t
        if isinstance(node, A.Binary):
            left = self.expr(node.left)
            right = self.expr(node.right)
            if node.op in ("+", "-", "*", "/", "//", "%", "**"):
                if isinstance(left, T.AnyType) or isinstance(right, T.AnyType):
                    return T.ANY
                if node.op == "+" and (isinstance(left, T.Prim) and left.name == "str"):
                    return T.STR
                if isinstance(left, T.Prim) and left.name == "float" or isinstance(right, T.Prim) and right.name == "float":
                    return T.FLOAT
                if isinstance(left, T.Prim) and left.name == "int" and isinstance(right, T.Prim) and right.name == "int":
                    return T.FLOAT if node.op == "/" else T.INT
                return T.ANY
            return T.ANY
        if isinstance(node, A.BoolOp):
            self.expr(node.left)
            self.expr(node.right)
            return T.ANY
        if isinstance(node, A.Compare):
            self.expr(node.left)
            for c in node.comparators:
                self.expr(c)
            return T.BOOL
        if isinstance(node, A.Ternary):
            self.expr(node.cond)
            a = self.expr(node.body)
            b = self.expr(node.orelse)
            return a if T.consistent(a, b) else T.ANY
        if isinstance(node, A.Call):
            ft = self.expr(node.func)
            args = [self.expr(a) for a in node.args]
            for kw in node.keywords:
                self.expr(kw.value)
            if isinstance(ft, T.FuncType):
                for i, (got, expected) in enumerate(zip(args, ft.params)):
                    if not T.consistent(got, expected):
                        self.err(node, f"argument {i + 1}: {got} not consistent with {expected}")
                return ft.returns
            return T.ANY
        if isinstance(node, A.Index):
            self.expr(node.value)
            self.expr(node.index)
            return T.ANY
        if isinstance(node, A.Slice):
            self.expr(node.value)
            if node.start:
                self.expr(node.start)
            if node.stop:
                self.expr(node.stop)
            return T.ANY
        if isinstance(node, A.Attribute):
            self.expr(node.value)
            return T.ANY
        return T.ANY


def check(program, path="<stdin>"):
    checker = Checker(path)
    return checker.check(program)
