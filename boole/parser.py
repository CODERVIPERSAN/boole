"""Parser for Boole. Indentation blocks, Python-like expressions, gradual types."""

from boole import ast as A
from boole.errors import BooleError
from boole.lexer import Lexer, module_is_static


class Parser:
    def __init__(self, tokens, path="<stdin>", static=False):
        self.tokens = tokens
        self.path = path
        self.static = static
        self.i = 0

    def cur(self):
        return self.tokens[self.i]

    def check(self, *kinds):
        return self.cur().kind in kinds

    def match(self, *kinds):
        if self.check(*kinds):
            t = self.cur()
            self.i += 1
            return t
        return None

    def expect(self, kind, message=None):
        if self.check(kind):
            t = self.cur()
            self.i += 1
            return t
        got = self.cur()
        raise BooleError(
            "SyntaxError",
            message or f"expected {kind}, got {got.kind}",
            got.line,
            got.col,
        )

    def skip_newlines(self):
        while self.match("NEWLINE"):
            pass

    def loc(self, token=None):
        t = token or self.cur()
        return t.line, t.col

    def parse(self):
        self.skip_newlines()
        body = []
        while not self.check("EOF"):
            body.append(self.statement())
            self.skip_newlines()
        return A.Program(body=body, static=self.static, line=1, col=1)

    def statement(self):
        if self.check("static"):
            return self.static_def()
        if self.check("def"):
            return self.func_def(is_static=False)
        if self.check("class"):
            return self.class_def()
        if self.check("if"):
            return self.if_stmt()
        if self.check("while"):
            return self.while_stmt()
        if self.check("for"):
            return self.for_stmt()
        if self.check("try"):
            return self.try_stmt()
        if self.check("return"):
            return self.return_stmt()
        if self.check("raise"):
            return self.raise_stmt()
        if self.check("assert"):
            return self.assert_stmt()
        if self.check("import"):
            return self.import_stmt()
        if self.check("pass"):
            t = self.expect("pass")
            self.expect("NEWLINE")
            return A.PassStmt(line=t.line, col=t.col)
        if self.check("break"):
            t = self.expect("break")
            self.expect("NEWLINE")
            return A.BreakStmt(line=t.line, col=t.col)
        if self.check("continue"):
            t = self.expect("continue")
            self.expect("NEWLINE")
            return A.ContinueStmt(line=t.line, col=t.col)
        return self.simple_stmt()

    def static_def(self):
        self.expect("static")
        if not self.check("def"):
            raise BooleError("SyntaxError", "expected def after static", self.cur().line, self.cur().col)
        return self.func_def(is_static=True)

    def func_def(self, is_static):
        t = self.expect("def")
        name = self.expect("IDENT").value
        self.expect("(")
        params = []
        if not self.check(")"):
            params.append(self.param())
            while self.match(","):
                if self.check(")"):
                    break
                params.append(self.param())
        self.expect(")")
        returns = None
        if self.match("->"):
            returns = self.type_expr()
        self.expect(":")
        body = self.block()
        force_static = is_static or self.static or returns is not None or any(p.typ for p in params)
        return A.FuncDef(
            name=name,
            params=params,
            returns=returns,
            body=body,
            is_static=force_static,
            line=t.line,
            col=t.col,
        )

    def param(self):
        name_t = self.expect("IDENT")
        typ = None
        default = None
        if self.match(":"):
            typ = self.type_expr()
        if self.match("="):
            default = self.expression()
        return A.Param(name=name_t.value, typ=typ, default=default, line=name_t.line, col=name_t.col)

    def class_def(self):
        t = self.expect("class")
        name = self.expect("IDENT").value
        base = None
        if self.match("("):
            if self.check("IDENT"):
                base = self.expect("IDENT").value
            self.expect(")")
        self.expect(":")
        body = self.block()
        return A.ClassDef(name=name, base=base, body=body, line=t.line, col=t.col)

    def if_stmt(self):
        t = self.expect("if")
        cond = self.expression()
        self.expect(":")
        body = self.block()
        elifs = []
        while self.check("elif"):
            self.expect("elif")
            econd = self.expression()
            self.expect(":")
            ebody = self.block()
            elifs.append((econd, ebody))
        else_body = None
        if self.match("else"):
            self.expect(":")
            else_body = self.block()
        return A.IfStmt(cond=cond, body=body, elifs=elifs, else_body=else_body, line=t.line, col=t.col)

    def while_stmt(self):
        t = self.expect("while")
        cond = self.expression()
        self.expect(":")
        body = self.block()
        return A.WhileStmt(cond=cond, body=body, line=t.line, col=t.col)

    def for_stmt(self):
        t = self.expect("for")
        name = self.expect("IDENT").value
        self.expect("in")
        iterable = self.expression()
        self.expect(":")
        body = self.block()
        return A.ForStmt(name=name, iterable=iterable, body=body, line=t.line, col=t.col)

    def try_stmt(self):
        t = self.expect("try")
        self.expect(":")
        body = self.block()
        handlers = []
        while self.check("except"):
            self.expect("except")
            exc = "Exception"
            as_name = None
            if self.check("IDENT"):
                exc = self.expect("IDENT").value
                if self.check("IDENT") and self.cur().value == "as":
                    self.i += 1
                    as_name = self.expect("IDENT").value
            self.expect(":")
            hbody = self.block()
            handlers.append((exc, as_name, hbody))
        final = None
        if self.match("finally"):
            self.expect(":")
            final = self.block()
        if not handlers and final is None:
            raise BooleError("SyntaxError", "try needs except or finally", t.line, t.col)
        return A.TryStmt(body=body, handlers=handlers, final=final, line=t.line, col=t.col)

    def return_stmt(self):
        t = self.expect("return")
        value = None
        if not self.check("NEWLINE", "DEDENT", "EOF"):
            value = self.expression()
        self.expect("NEWLINE")
        return A.ReturnStmt(value=value, line=t.line, col=t.col)

    def raise_stmt(self):
        t = self.expect("raise")
        exc = "RuntimeError"
        message = None
        if self.check("IDENT"):
            exc = self.expect("IDENT").value
            if self.match("("):
                if not self.check(")"):
                    message = self.expression()
                self.expect(")")
        self.expect("NEWLINE")
        return A.RaiseStmt(exc=exc, message=message, line=t.line, col=t.col)

    def assert_stmt(self):
        t = self.expect("assert")
        cond = self.expression()
        message = None
        if self.match(","):
            message = self.expression()
        self.expect("NEWLINE")
        return A.AssertStmt(cond=cond, message=message, line=t.line, col=t.col)

    def import_stmt(self):
        t = self.expect("import")
        name = self.expect("IDENT").value
        while self.match("."):
            name += "." + self.expect("IDENT").value
        self.expect("NEWLINE")
        return A.ImportStmt(name=name, line=t.line, col=t.col)

    def block(self):
        self.expect("NEWLINE")
        self.expect("INDENT")
        body = []
        while not self.check("DEDENT", "EOF"):
            body.append(self.statement())
            self.skip_newlines()
        self.expect("DEDENT")
        return body

    def simple_stmt(self):
        line, col = self.loc()
        # annotated assign: name: Type = value  or  name: Type
        if self.check("IDENT"):
            save = self.i
            name_t = self.expect("IDENT")
            if self.match(":"):
                if self.check("=", "NEWLINE"):
                    # bare annotation without type name — invalid; restore
                    self.i = save
                else:
                    typ = self.type_expr()
                    value = None
                    if self.match("="):
                        value = self.expression()
                    self.expect("NEWLINE")
                    return A.AnnAssign(
                        target=A.Name(id=name_t.value, line=name_t.line, col=name_t.col),
                        typ=typ,
                        value=value,
                        line=line,
                        col=col,
                    )
            self.i = save

        expr = self.expression()
        if self.match("="):
            value = self.expression()
            self.expect("NEWLINE")
            return A.Assign(target=expr, value=value, line=line, col=col)
        for op in ("+", "-", "*", "/", "//", "%", "**"):
            # not used; augassign via token peek
            pass
        if self.check("+", "-", "*", "/", "//", "%", "**") and False:
            pass
        # augmented assignment
        if self.cur().kind in ("+", "-", "*", "/", "//", "%", "**") and self._peek_eq():
            op = self.cur().kind
            self.i += 1
            self.expect("=")
            value = self.expression()
            self.expect("NEWLINE")
            return A.AugAssign(target=expr, op=op, value=value, line=line, col=col)

        self.expect("NEWLINE")
        return A.ExprStmt(expr=expr, line=line, col=col)

    def _peek_eq(self):
        if self.i + 1 >= len(self.tokens):
            return False
        return self.tokens[self.i + 1].kind == "="

    def type_expr(self):
        left = self.type_atom()
        if self.match("|"):
            options = [left]
            options.append(self.type_atom())
            while self.match("|"):
                options.append(self.type_atom())
            return A.UnionType(options=options, line=left.line, col=left.col)
        return left

    def type_atom(self):
        if self.check("None"):
            t = self.expect("None")
            return A.NamedType(name="None", line=t.line, col=t.col)
        name_t = self.expect("IDENT")
        if self.match("["):
            args = [self.type_expr()]
            while self.match(","):
                if self.check("]"):
                    break
                args.append(self.type_expr())
            self.expect("]")
            return A.AppType(name=name_t.value, args=args, line=name_t.line, col=name_t.col)
        return A.NamedType(name=name_t.value, line=name_t.line, col=name_t.col)

    def expression(self):
        return self.ternary()

    def ternary(self):
        node = self.or_expr()
        if self.match("if"):
            cond = self.or_expr()
            self.expect("else")
            orelse = self.ternary()
            return A.Ternary(body=node, cond=cond, orelse=orelse, line=node.line, col=node.col)
        return node

    def or_expr(self):
        node = self.and_expr()
        while self.match("or"):
            right = self.and_expr()
            node = A.BoolOp(op="or", left=node, right=right, line=node.line, col=node.col)
        return node

    def and_expr(self):
        node = self.not_expr()
        while self.match("and"):
            right = self.not_expr()
            node = A.BoolOp(op="and", left=node, right=right, line=node.line, col=node.col)
        return node

    def not_expr(self):
        if self.match("not"):
            t = self.tokens[self.i - 1]
            return A.Unary(op="not", operand=self.not_expr(), line=t.line, col=t.col)
        return self.compare()

    def compare(self):
        node = self.bitwise()
        ops = []
        comps = []
        while True:
            if self.match("=="):
                ops.append("==")
            elif self.match("!="):
                ops.append("!=")
            elif self.match("<"):
                ops.append("<")
            elif self.match(">"):
                ops.append(">")
            elif self.match("<="):
                ops.append("<=")
            elif self.match(">="):
                ops.append(">=")
            elif self.match("in"):
                ops.append("in")
            elif self.check("not") and self.i + 1 < len(self.tokens) and self.tokens[self.i + 1].kind == "in":
                self.i += 2
                ops.append("not in")
            elif self.match("is"):
                if self.match("not"):
                    ops.append("is not")
                else:
                    ops.append("is")
            else:
                break
            comps.append(self.bitwise())
        if ops:
            return A.Compare(left=node, ops=ops, comparators=comps, line=node.line, col=node.col)
        return node

    def bitwise(self):
        # no bitwise in v0.1 surface; fall through
        return self.arith()

    def _is_augassign_op(self):
        return self._peek_eq()

    def arith(self):
        node = self.term()
        while True:
            if self.check("+", "-") and self._is_augassign_op():
                break
            if self.match("+"):
                right = self.term()
                node = A.Binary(op="+", left=node, right=right, line=node.line, col=node.col)
            elif self.match("-"):
                right = self.term()
                node = A.Binary(op="-", left=node, right=right, line=node.line, col=node.col)
            else:
                break
        return node

    def term(self):
        node = self.power()
        while True:
            if self.check("*", "/", "//", "%") and self._is_augassign_op():
                break
            if self.match("*"):
                right = self.power()
                node = A.Binary(op="*", left=node, right=right, line=node.line, col=node.col)
            elif self.match("/"):
                right = self.power()
                node = A.Binary(op="/", left=node, right=right, line=node.line, col=node.col)
            elif self.match("//"):
                right = self.power()
                node = A.Binary(op="//", left=node, right=right, line=node.line, col=node.col)
            elif self.match("%"):
                right = self.power()
                node = A.Binary(op="%", left=node, right=right, line=node.line, col=node.col)
            else:
                break
        return node

    def power(self):
        node = self.unary()
        if self.check("**") and self._is_augassign_op():
            return node
        if self.match("**"):
            right = self.power()
            return A.Binary(op="**", left=node, right=right, line=node.line, col=node.col)
        return node

    def unary(self):
        if self.match("+"):
            t = self.tokens[self.i - 1]
            return A.Unary(op="+", operand=self.unary(), line=t.line, col=t.col)
        if self.match("-"):
            t = self.tokens[self.i - 1]
            return A.Unary(op="-", operand=self.unary(), line=t.line, col=t.col)
        return self.postfix()

    def postfix(self):
        node = self.atom()
        while True:
            if self.match("("):
                args = []
                keywords = []
                if not self.check(")"):
                    while True:
                        if (
                            self.check("IDENT")
                            and self.i + 1 < len(self.tokens)
                            and self.tokens[self.i + 1].kind == "="
                        ):
                            name = self.expect("IDENT").value
                            self.expect("=")
                            keywords.append(A.Keyword(name=name, value=self.expression()))
                        else:
                            if keywords:
                                raise BooleError(
                                    "SyntaxError",
                                    "positional argument after keyword",
                                    self.cur().line,
                                    self.cur().col,
                                )
                            args.append(self.expression())
                        if not self.match(","):
                            break
                        if self.check(")"):
                            break
                self.expect(")")
                node = A.Call(func=node, args=args, keywords=keywords, line=node.line, col=node.col)
            elif self.match("["):
                start = None
                if not self.check(":", "]"):
                    start = self.expression()
                if self.match(":"):
                    stop = None
                    if not self.check("]"):
                        stop = self.expression()
                    self.expect("]")
                    node = A.Slice(value=node, start=start, stop=stop, line=node.line, col=node.col)
                else:
                    self.expect("]")
                    node = A.Index(value=node, index=start, line=node.line, col=node.col)
            elif self.match("."):
                attr = self.expect("IDENT").value
                node = A.Attribute(value=node, attr=attr, line=node.line, col=node.col)
            else:
                break
        return node

    def atom(self):
        if self.check("NUMBER"):
            t = self.expect("NUMBER")
            return A.Literal(value=t.value, line=t.line, col=t.col)
        if self.check("STRING"):
            t = self.expect("STRING")
            return A.Literal(value=t.value, line=t.line, col=t.col)
        if self.check("FSTRING"):
            t = self.expect("FSTRING")
            parts = []
            for part in t.value:
                if part[0] == "text":
                    parts.append(("text", part[1]))
                else:
                    _, src, eline, ecol = part
                    sub = Parser(Lexer(src + "\n", self.path).lex(), self.path, self.static)
                    parts.append(("expr", sub.expression()))
            return A.FString(parts=parts, line=t.line, col=t.col)
        if self.check("True"):
            t = self.expect("True")
            return A.Literal(value=True, line=t.line, col=t.col)
        if self.check("False"):
            t = self.expect("False")
            return A.Literal(value=False, line=t.line, col=t.col)
        if self.check("None"):
            t = self.expect("None")
            return A.Literal(value=None, line=t.line, col=t.col)
        if self.check("IDENT"):
            t = self.expect("IDENT")
            return A.Name(id=t.value, line=t.line, col=t.col)
        if self.match("("):
            if self.check(")"):
                raise BooleError("SyntaxError", "empty tuple not supported in v0.1", self.cur().line, self.cur().col)
            node = self.expression()
            self.expect(")")
            return node
        if self.match("["):
            elts = []
            if not self.check("]"):
                elts.append(self.expression())
                while self.match(","):
                    if self.check("]"):
                        break
                    elts.append(self.expression())
            self.expect("]")
            return A.ListLit(elts=elts, line=self.tokens[self.i - 1].line, col=1)
        if self.match("{"):
            keys = []
            values = []
            if not self.check("}"):
                keys.append(self.expression())
                self.expect(":")
                values.append(self.expression())
                while self.match(","):
                    if self.check("}"):
                        break
                    keys.append(self.expression())
                    self.expect(":")
                    values.append(self.expression())
            self.expect("}")
            return A.DictLit(keys=keys, values=values, line=1, col=1)
        t = self.cur()
        raise BooleError("SyntaxError", f"unexpected {t.kind}", t.line, t.col)


def parse(source, path="<stdin>"):
    static = module_is_static(source)
    tokens = Lexer(source, path).lex()
    return Parser(tokens, path, static).parse()
