"""Built-in functions for the Boole runtime."""


def make_builtins(runtime):
    def boole_print(*args, sep=" ", end="\n"):
        text = sep.join(str(a) for a in args)
        runtime.stdout.write(text + end)
        return None

    def boole_len(x):
        return len(x)

    def boole_range(*args):
        return list(range(*args))

    def boole_str(x=""):
        return str(x)

    def boole_int(x=0):
        return int(x)

    def boole_float(x=0.0):
        return float(x)

    def boole_bool(x=False):
        return bool(x)

    def boole_list(x=None):
        if x is None:
            return []
        return list(x)

    def boole_dict(*args, **kwargs):
        if args:
            return dict(args[0])
        return dict(**kwargs)

    def boole_type(x):
        if x is None:
            return "None"
        if isinstance(x, bool):
            return "bool"
        if isinstance(x, int):
            return "int"
        if isinstance(x, float):
            return "float"
        if isinstance(x, str):
            return "str"
        if isinstance(x, list):
            return "list"
        if isinstance(x, dict):
            return "dict"
        return type(x).__name__

    def boole_isinstance(x, name):
        mapping = {
            "int": int,
            "float": float,
            "bool": bool,
            "str": str,
            "list": list,
            "dict": dict,
        }
        if isinstance(name, str) and name in mapping:
            # bool is a subclass of int — match Python for bool first
            if name == "int" and isinstance(x, bool):
                return False
            return isinstance(x, mapping[name])
        return isinstance(x, name) if isinstance(name, type) else False

    def boole_input(prompt=""):
        return input(prompt)

    def boole_open(path, mode="r", encoding="utf-8"):
        return open(path, mode, encoding=encoding)

    def boole_enumerate(x, start=0):
        return list(enumerate(x, start=start))

    def boole_zip(*args):
        return [list(row) for row in zip(*args)]

    def boole_sorted(x, reverse=False):
        return sorted(x, reverse=reverse)

    def boole_sum(x, start=0):
        return sum(x, start)

    def boole_min(*args):
        if len(args) == 1:
            return min(args[0])
        return min(args)

    def boole_max(*args):
        if len(args) == 1:
            return max(args[0])
        return max(args)

    def boole_abs(x):
        return abs(x)

    return {
        "print": boole_print,
        "len": boole_len,
        "range": boole_range,
        "str": boole_str,
        "int": boole_int,
        "float": boole_float,
        "bool": boole_bool,
        "list": boole_list,
        "dict": boole_dict,
        "type": boole_type,
        "isinstance": boole_isinstance,
        "input": boole_input,
        "open": boole_open,
        "enumerate": boole_enumerate,
        "zip": boole_zip,
        "sorted": boole_sorted,
        "sum": boole_sum,
        "min": boole_min,
        "max": boole_max,
        "abs": boole_abs,
        "Exception": Exception,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "RuntimeError": RuntimeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "AssertionError": AssertionError,
        "True": True,
        "False": False,
        "None": None,
    }
