"""Gradual types for Boole.

Ideas aligned with the Python typing specification (PSF License):
static annotations where written, dynamic elsewhere, Any at open boundaries.
https://typing.python.org/en/latest/spec/
"""

from __future__ import annotations

from boole import ast as A


class Type:
    def __str__(self):
        return self.render()

    def render(self):
        return "?"


class AnyType(Type):
    def render(self):
        return "Any"


class NoneType(Type):
    def render(self):
        return "None"


class Prim(Type):
    def __init__(self, name):
        self.name = name

    def render(self):
        return self.name


class ListType(Type):
    def __init__(self, item):
        self.item = item

    def render(self):
        return f"list[{self.item}]"


class DictType(Type):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def render(self):
        return f"dict[{self.key}, {self.value}]"


class FuncType(Type):
    def __init__(self, params, returns):
        self.params = params
        self.returns = returns

    def render(self):
        args = ", ".join(str(p) for p in self.params)
        return f"({args}) -> {self.returns}"


class Union(Type):
    def __init__(self, options):
        self.options = options

    def render(self):
        return " | ".join(str(o) for o in self.options)


ANY = AnyType()
NONE = NoneType()
INT = Prim("int")
FLOAT = Prim("float")
BOOL = Prim("bool")
STR = Prim("str")


def from_ast(node):
    if node is None:
        return ANY
    if isinstance(node, A.NamedType):
        name = node.name
        mapping = {
            "int": INT,
            "float": FLOAT,
            "bool": BOOL,
            "str": STR,
            "String": STR,
            "Int": INT,
            "Float": FLOAT,
            "Bool": BOOL,
            "None": NONE,
            "Any": ANY,
            "list": ListType(ANY),
            "dict": DictType(ANY, ANY),
        }
        if name in mapping:
            return mapping[name]
        return Prim(name)
    if isinstance(node, A.AppType):
        if node.name in ("list", "List"):
            return ListType(from_ast(node.args[0]) if node.args else ANY)
        if node.name in ("dict", "Dict"):
            key = from_ast(node.args[0]) if len(node.args) > 0 else ANY
            val = from_ast(node.args[1]) if len(node.args) > 1 else ANY
            return DictType(key, val)
        return Prim(node.name)
    if isinstance(node, A.UnionType):
        return Union([from_ast(o) for o in node.options])
    return ANY


def from_value(value):
    if value is None:
        return NONE
    if isinstance(value, bool):
        return BOOL
    if isinstance(value, int):
        return INT
    if isinstance(value, float):
        return FLOAT
    if isinstance(value, str):
        return STR
    if isinstance(value, list):
        if not value:
            return ListType(ANY)
        return ListType(from_value(value[0]))
    if isinstance(value, dict):
        if not value:
            return DictType(ANY, ANY)
        k = next(iter(value))
        return DictType(from_value(k), from_value(value[k]))
    return ANY


def consistent(a, b):
    """Gradual consistency: Any is consistent with everything."""
    if isinstance(a, AnyType) or isinstance(b, AnyType):
        return True
    if isinstance(a, NoneType) and isinstance(b, NoneType):
        return True
    if isinstance(a, Prim) and isinstance(b, Prim):
        if a.name == b.name:
            return True
        if {a.name, b.name} <= {"int", "float"}:
            return True
        return False
    if isinstance(a, ListType) and isinstance(b, ListType):
        return consistent(a.item, b.item)
    if isinstance(a, DictType) and isinstance(b, DictType):
        return consistent(a.key, b.key) and consistent(a.value, b.value)
    if isinstance(a, Union):
        return any(consistent(o, b) for o in a.options)
    if isinstance(b, Union):
        return any(consistent(a, o) for o in b.options)
    if isinstance(a, FuncType) and isinstance(b, FuncType):
        if len(a.params) != len(b.params):
            return False
        return all(consistent(x, y) for x, y in zip(a.params, b.params)) and consistent(
            a.returns, b.returns
        )
    return False
