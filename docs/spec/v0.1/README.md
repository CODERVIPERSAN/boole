# Boole Language Specification v0.1

**Status:** as-built outline matching the runnable toolchain (`boole test` = 100/100).  
**Marks:** **[implemented]** ships today · **[planned]** listed in `PLAN.md`, not a v0.1 requirement.

This document describes the **Boole language** (layer 1). The adaptive / natural-language execution engine is documented separately under `docs/engine/`.

---

## 1. Goals

**[implemented]**

- Python-like syntax for scripts and learning
- Gradual typing for production modules (`static def`, `# boole: static`)
- Memory-safe heap via refcounted runtime
- Native execution through C codegen + `clang -O3 -flto`
- Interpreter fallback for edges the native backend rejects

**[planned]** (not v0.1)

- Ownership / unique-by-default, `task` concurrency, zero-cost generics
- `Boole.toml`, `boole pkg`, `boole fmt`
- Self-hosting; full stdlib and package registry

---

## 2. Lexical structure

**[implemented]**

- UTF-8 `.boole` source files
- Indentation with spaces only (tabs rejected)
- Comments: `# ...` to end of line
- Module directive: first meaningful line `# boole: static` forces static checking for the file
- Identifiers, integer/float/string literals, f-strings

**[planned]**

- Raw / byte string forms beyond current literals
- Doc-comment conventions for tooling

---

## 3. Grammar (subset)

**[implemented]**

```
Program     = statement*
statement   = def | static_def | class | if | while | for
            | try | return | raise | assert | import
            | pass | break | continue
            | assign | ann_assign | aug_assign | expr_stmt
expression  = literal | name | list | dict | fstring
            | call | index | slice
            | unary | binary | boolop | compare | ternary
```

- `def` / `static def` with optional parameter and return annotations
- `class` with optional single base; methods take `self`
- Control: `if` / `elif` / `else`, `while`, `for … in …`
- Exceptions: `try` / `except` / `finally`, `raise`
- Modules: `import name` (stdlib or sibling `.boole`)

**[planned]**

- Enums + exhaustive `match`
- Generics syntax beyond `list[T]` / `dict[K,V]` annotations
- `defer`, `unsafe`, `task` forms

---

## 4. Type system

**[implemented]**

- Unannotated names and parameters are `Any`
- Annotations: `int`, `float`, `bool`, `str`, `None`, `Any`, `list[T]`, `dict[K,V]`, unions `A|B`
- Consistency: `Any` is consistent with every type (gradual)
- `static def` and `# boole: static` require parameter and return annotations
- Dynamic scripts may rebind a name to another type (becomes `Any`)
- Checker: `boole check`; also runs when the program is marked static or `--check` is set

**[planned]**

- Unique-by-default + `Rc` + borrow-style rules
- Zero-cost generics (monomorphization)
- Stricter static whole-program modes

---

## 5. Memory model

**[implemented]**

- Native: `none` / `bool` / `int` / `float` unboxed where possible; `str` / `list` / `dict` / objects refcounted
- No manual `free` in Boole source
- Runtime: `runtime/boole_rt.c` + OOP helpers in `runtime/boole_oop.c`

**[planned]**

- Unique ownership + `defer`
- `no_runtime` / embedded subset
- Optional tracing GC (not required for v0.1)

---

## 6. Concurrency

**[planned]**

- Not in v0.1
- Future: `task` concurrency without shared-memory data races

---

## 7. Error handling

**[implemented]**

- Interpreter: exception objects; `try` / `except` / `finally` work
- Native: `try` / `except` / `finally` via codegen; unrecoverable errors use `bv_die`
- CLI: native-unsupported constructs print a note and fall back to the interpreter unless `--strict-native`

**[planned]**

- Richer diagnostics (file:line + hints) across all phases

---

## 8. Modules and packages

**[implemented]**

- `import math` | `import json` (native and interpreter where supported)
- `import sys` — interpreter-only in native v0.1 (falls back)
- Local `import name` loads sibling `name.boole`
- Native can inline/import local modules and selected stdlib; remaining edges use interp fallback

**[planned]**

- `Boole.toml` manifest
- `boole pkg` + registry + lockfile / workspaces

---

## 9. Compiler architecture

**[implemented]**

```
.source.boole
    → lexer → parser → AST
         → gradual checker
         → C codegen (int unbox, classes, try, import)
              → clang -O3 -flto → native binary
         → interpreter (fallback / --interp)
```

Host modules: `boole/lexer.py`, `parser.py`, `checker.py`, `cgen.py`, `native.py`, `interpreter.py`, `cli.py`.

**[planned]**

- LLVM IR backend
- Debug info (gdb/lldb)
- Documented LTO / PGO release profile
- Adaptive AI execution engine selecting backends (see `docs/engine/`)

---

## 10. Builtins

**[implemented]**

`print`, `len`, `range`, `str`, `int`, `float`, `bool`, `list`, `dict`, `type`, `isinstance`, `sorted`, `min`, `max`, `sum`, `abs`, `enumerate`, `zip`, `open`, `input`, and related helpers used by the test suite.

**[planned]**

- Full `std/` (fs, path, process, regex, http, time, random, test)
- C FFI and Python FFI bridges

---

## 11. Toolchain conventions

**[implemented]**

| Command | Role |
| --- | --- |
| `boole run file.boole` | native compile + run; auto-fallback to interp |
| `boole run --interp` | force interpreter |
| `boole run --strict-native` | no interp fallback |
| `boole build -o out` | emit native binary |
| `boole check` | type-check |
| `boole opt` | static vs dynamic function report |
| `boole test` / `boole bench` | proof suite |
| `boole lex` / `boole parse` | debug front end |

**[planned]**

- `boole fmt`
- `boole pkg`
- Package manifest: `Boole.toml`

---

## 12. Non-goals for v0.1

- Self-hosting compiler
- Full borrow checker / ownership as default
- Tracing GC as the primary heap
- Claiming “natural language → binary with no IR” inside the language itself (that is engine research; see `docs/engine/`)
- Web / AI frameworks in-tree
- Renaming the language (name is **Boole**; Aethon was rejected for collisions)
