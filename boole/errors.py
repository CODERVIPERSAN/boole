"""Errors for the Boole compiler and interpreter."""


class BooleError(Exception):
    """A syntax, type, or runtime error with a source location."""

    def __init__(self, kind, message, line=1, col=1):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.line = line
        self.col = col

    def format(self, path=None):
        where = f"{path}:" if path else ""
        return f"{where}{self.line}:{self.col}: {self.kind}: {self.message}"


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass
