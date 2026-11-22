"""Lexer for Boole. Indentation follows Python: spaces only, blocks via indent."""

from boole.errors import BooleError

KEYWORDS = {
    "def", "if", "elif", "else", "while", "for", "in", "return", "and", "or",
    "not", "pass", "break", "continue", "class", "static", "try", "except",
    "finally", "raise", "assert", "import", "is", "True", "False", "None",
}


class Token:
    def __init__(self, kind, value, line, col):
        self.kind = kind
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.kind!r}, {self.value!r}, {self.line}:{self.col})"


class Lexer:
    def __init__(self, source, path="<stdin>"):
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        if self.source and not self.source.endswith("\n"):
            self.source += "\n"
        self.path = path
        self.i = 0
        self.line = 1
        self.col = 1
        self.tokens = []
        self.indents = [0]
        self.paren = 0
        self.at_line_start = True

    def error(self, message):
        raise BooleError("SyntaxError", message, self.line, self.col)

    def peek(self, k=0):
        j = self.i + k
        if j >= len(self.source):
            return ""
        return self.source[j]

    def bump(self):
        ch = self.source[self.i]
        self.i += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def emit(self, kind, value, line, col):
        self.tokens.append(Token(kind, value, line, col))

    def lex(self):
        while self.i < len(self.source):
            if self.at_line_start and self.paren == 0:
                self._line_start()
                continue
            if self.at_line_start and self.paren > 0:
                self._skip_continued_indent()
                continue
            self._token()
        if not self.at_line_start:
            line = self.line
            col = self.col
            self.emit("NEWLINE", "\n", line, max(col - 1, 1))
        while len(self.indents) > 1:
            self.indents.pop()
            self.emit("DEDENT", "", self.line, self.col)
        self.emit("EOF", "", self.line, self.col)
        return self.tokens

    def _line_start(self):
        start_line = self.line
        start_col = self.col
        n = 0
        while self.peek() == " ":
            self.bump()
            n += 1
        if self.peek() == "\t":
            self.error("indent with spaces, not tabs")
        if self.peek() in ("\n", "#", ""):
            if self.peek() == "#":
                while self.peek() not in ("\n", ""):
                    self.bump()
            if self.peek() == "\n":
                self.bump()
            self.at_line_start = True
            return
        self._set_indent(n, start_line, start_col)
        self.at_line_start = False

    def _set_indent(self, n, line, col):
        if n == self.indents[-1]:
            return
        if n > self.indents[-1]:
            self.indents.append(n)
            self.emit("INDENT", n, line, col)
            return
        while n < self.indents[-1]:
            self.indents.pop()
            self.emit("DEDENT", "", line, col)
        if n != self.indents[-1]:
            raise BooleError("SyntaxError", "unindent does not match any outer level", line, col)

    def _skip_continued_indent(self):
        while self.peek() in (" ", "\t"):
            if self.peek() == "\t":
                self.error("indent with spaces, not tabs")
            self.bump()
        if self.peek() == "#":
            while self.peek() not in ("\n", ""):
                self.bump()
        if self.peek() == "\n":
            self.bump()
            self.at_line_start = True
            return
        self.at_line_start = False

    def _token(self):
        ch = self.peek()
        if ch in (" ", "\t"):
            if ch == "\t":
                self.error("indent with spaces, not tabs")
            self.bump()
            return
        if ch == "#":
            while self.peek() not in ("\n", ""):
                self.bump()
            return
        if ch == "\n":
            line, col = self.line, self.col
            self.bump()
            if self.paren == 0:
                self.emit("NEWLINE", "\n", line, col)
                self.at_line_start = True
            return
        line, col = self.line, self.col
        if ch in ("f", "F") and self.peek(1) in ("'", '"'):
            self._fstring(line, col)
            return
        if ch in ("'", '"'):
            self.emit("STRING", self._string(ch), line, col)
            return
        if ch.isdigit() or (ch == "." and self.peek(1).isdigit()):
            self.emit("NUMBER", self._number(), line, col)
            return
        if ch.isalpha() or ch == "_":
            word = self._word()
            kind = word if word in KEYWORDS else "IDENT"
            self.emit(kind, word, line, col)
            return
        two = ch + self.peek(1)
        if two in ("//", "**", "==", "!=", "<=", ">=", "->"):
            self.bump()
            self.bump()
            self.emit(two, two, line, col)
            return
        if ch in "()[]{}:,.":
            self.bump()
            if ch in "([{":
                self.paren += 1
            elif ch in ")]}":
                if self.paren == 0:
                    self.error("unmatched closing bracket")
                self.paren -= 1
            self.emit(ch, ch, line, col)
            return
        if ch in "+-*/%<>=!":
            self.bump()
            self.emit(ch, ch, line, col)
            return
        self.error(f"unexpected character {ch!r}")

    def _word(self):
        chars = []
        while self.peek().isalnum() or self.peek() == "_":
            chars.append(self.bump())
        return "".join(chars)

    def _number(self):
        chars = []
        is_float = False
        if self.peek() == ".":
            is_float = True
            chars.append(self.bump())
        while self.peek().isdigit():
            chars.append(self.bump())
        if self.peek() == "." and not is_float:
            is_float = True
            chars.append(self.bump())
            while self.peek().isdigit():
                chars.append(self.bump())
        if self.peek() in ("e", "E"):
            is_float = True
            chars.append(self.bump())
            if self.peek() in ("+", "-"):
                chars.append(self.bump())
            if not self.peek().isdigit():
                self.error("bad number exponent")
            while self.peek().isdigit():
                chars.append(self.bump())
        text = "".join(chars)
        return float(text) if is_float else int(text)

    def _string(self, quote):
        self.bump()
        chars = []
        while True:
            ch = self.peek()
            if ch == "":
                self.error("unterminated string")
            if ch == "\n":
                self.error("unterminated string")
            if ch == quote:
                self.bump()
                return "".join(chars)
            if ch == "\\":
                chars.append(self._escape())
                continue
            chars.append(self.bump())

    def _escape(self):
        self.bump()
        ch = self.peek()
        mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", '"': '"'}
        if ch in mapping:
            self.bump()
            return mapping[ch]
        self.error(f"unknown string escape \\{ch}")

    def _fstring(self, line, col):
        self.bump()
        quote = self.bump()
        parts = []
        buf = []
        while True:
            ch = self.peek()
            if ch in ("", "\n"):
                self.error("unterminated f-string")
            if ch == quote:
                self.bump()
                if buf:
                    parts.append(("text", "".join(buf)))
                self.emit("FSTRING", parts, line, col)
                return
            if ch == "{":
                if self.peek(1) == "{":
                    self.bump()
                    self.bump()
                    buf.append("{")
                    continue
                if buf:
                    parts.append(("text", "".join(buf)))
                    buf = []
                self.bump()
                expr_line, expr_col = self.line, self.col
                expr = self._f_expr()
                parts.append(("expr", expr, expr_line, expr_col))
                continue
            if ch == "}":
                if self.peek(1) == "}":
                    self.bump()
                    self.bump()
                    buf.append("}")
                    continue
                self.error("single '}' in f-string, use '}}'")
            if ch == "\\":
                buf.append(self._escape())
                continue
            buf.append(self.bump())

    def _f_expr(self):
        chars = []
        depth = 1
        in_str = ""
        while self.i < len(self.source):
            ch = self.peek()
            if in_str:
                chars.append(self.bump())
                if ch == "\\":
                    if self.peek():
                        chars.append(self.bump())
                    continue
                if ch == in_str:
                    in_str = ""
                continue
            if ch in ("'", '"'):
                in_str = ch
                chars.append(self.bump())
                continue
            if ch == "{":
                depth += 1
                chars.append(self.bump())
                continue
            if ch == "}":
                depth -= 1
                if depth == 0:
                    self.bump()
                    return "".join(chars).strip()
                chars.append(self.bump())
                continue
            if ch in ("", "\n"):
                self.error("unterminated expression in f-string")
            if ch == ":":
                self.error("f-string format specs are not in v0.1")
            chars.append(self.bump())
        self.error("unterminated expression in f-string")


def module_is_static(source):
    """True when the file starts with the production directive `# boole: static`."""
    seen = 0
    for line in source.splitlines():
        text = line.strip()
        if text == "" or text.startswith("#!"):
            continue
        seen += 1
        if text == "# boole: static":
            return True
        if seen >= 1:
            return False
    return False


def lex(source, path="<stdin>"):
    return Lexer(source, path).lex()
