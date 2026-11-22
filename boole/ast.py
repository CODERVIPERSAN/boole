"""Abstract syntax for Boole."""

from dataclasses import dataclass, field


@dataclass
class Node:
    line: int = 1
    col: int = 1


@dataclass
class Program(Node):
    body: list = field(default_factory=list)
    static: bool = False


@dataclass
class Param(Node):
    name: str = ""
    typ: object = None
    default: object = None


@dataclass
class FuncDef(Node):
    name: str = ""
    params: list = field(default_factory=list)
    returns: object = None
    body: list = field(default_factory=list)
    is_static: bool = False


@dataclass
class ClassDef(Node):
    name: str = ""
    base: str | None = None
    body: list = field(default_factory=list)


@dataclass
class IfStmt(Node):
    cond: object = None
    body: list = field(default_factory=list)
    elifs: list = field(default_factory=list)
    else_body: list | None = None


@dataclass
class WhileStmt(Node):
    cond: object = None
    body: list = field(default_factory=list)


@dataclass
class ForStmt(Node):
    name: str = ""
    iterable: object = None
    body: list = field(default_factory=list)


@dataclass
class TryStmt(Node):
    body: list = field(default_factory=list)
    handlers: list = field(default_factory=list)
    final: list | None = None


@dataclass
class ReturnStmt(Node):
    value: object = None


@dataclass
class RaiseStmt(Node):
    exc: str = "RuntimeError"
    message: object = None


@dataclass
class AssertStmt(Node):
    cond: object = None
    message: object = None


@dataclass
class Assign(Node):
    target: object = None
    value: object = None


@dataclass
class AnnAssign(Node):
    target: object = None
    typ: object = None
    value: object = None


@dataclass
class AugAssign(Node):
    target: object = None
    op: str = ""
    value: object = None


@dataclass
class ExprStmt(Node):
    expr: object = None


@dataclass
class PassStmt(Node):
    pass


@dataclass
class BreakStmt(Node):
    pass


@dataclass
class ContinueStmt(Node):
    pass


@dataclass
class ImportStmt(Node):
    name: str = ""


@dataclass
class Name(Node):
    id: str = ""


@dataclass
class Literal(Node):
    value: object = None


@dataclass
class ListLit(Node):
    elts: list = field(default_factory=list)


@dataclass
class DictLit(Node):
    keys: list = field(default_factory=list)
    values: list = field(default_factory=list)


@dataclass
class FString(Node):
    parts: list = field(default_factory=list)


@dataclass
class Unary(Node):
    op: str = ""
    operand: object = None


@dataclass
class Binary(Node):
    op: str = ""
    left: object = None
    right: object = None


@dataclass
class BoolOp(Node):
    op: str = ""
    left: object = None
    right: object = None


@dataclass
class Compare(Node):
    left: object = None
    ops: list = field(default_factory=list)
    comparators: list = field(default_factory=list)


@dataclass
class Ternary(Node):
    body: object = None
    cond: object = None
    orelse: object = None


@dataclass
class Call(Node):
    func: object = None
    args: list = field(default_factory=list)
    keywords: list = field(default_factory=list)


@dataclass
class Keyword(Node):
    name: str = ""
    value: object = None


@dataclass
class Index(Node):
    value: object = None
    index: object = None


@dataclass
class Slice(Node):
    value: object = None
    start: object = None
    stop: object = None


@dataclass
class Attribute(Node):
    value: object = None
    attr: str = ""


@dataclass
class NamedType(Node):
    name: str = ""


@dataclass
class AppType(Node):
    name: str = ""
    args: list = field(default_factory=list)


@dataclass
class UnionType(Node):
    options: list = field(default_factory=list)
