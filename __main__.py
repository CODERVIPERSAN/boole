"""Allow `python -m boole` when run from ~ (repo dir shadows the inner package)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _boot() -> int:
    # Prefer the real package at <repo>/boole/
    root = str(_ROOT)
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    for name in list(sys.modules):
        if name == "boole" or name.startswith("boole."):
            del sys.modules[name]
    from boole.cli import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_boot())
