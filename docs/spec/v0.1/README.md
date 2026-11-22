# Boole Language Specification v0.1

**Status:** matches the runnable toolchain (`boole test` = 100/100).

## 1. Goals

- Python-like syntax for scripts and learning
- Gradual typing for production modules
- Memory-safe heap via refcounted runtime
- Native execution through C codegen + clang

## 2. Lexical structure

- UTF-8 `.boole` files; spaces for indent (tabs rejected)
- Comments: `# ...`
- Module directive: first meaningful line `# boole: static`

## 3. Grammar (subset)

Program = statement*
Statements: `def` / `static def`, `class`, `if`/`elif`/`else`, `while`, `for`, `try`/`except`/`finally`, `return`, `raise`, `assert`, `import`, `pass`/`break`/`continue`, assign, ann-assign, aug-assign, expr
Expressions: literals, names, lists, dicts, f-strings, calls, index/slice, unary/binary/bool/compare/ternary

## 4. Type system

- Unannotated names and parameters are `Any`
- Annotations: `int|float|bool|str|None|Any|list[T]|dict[K,V]|A|B`
- Consistency: `Any` is consistent with every type
- `static def` and `# boole: static` require parameter and return annotations
- Dynamic scripts may rebind a name to another type (type becomes `Any`)

## 5. Memory model

- Native: none/bool/int/float unboxed; str/list/dict refcounted
- No manual deallocation in Boole source

## 6. Concurrency

- Not in v0.1 (planned: `task`)

## 7. Errors

- Interpreter: Python exceptions; `try`/`except` works
- Native: `bv_die` for unrecoverable errors; prefer interp for exception-heavy code

## 8. Modules

- Interpreter: `import math|json|sys` and local `import name` → `name.boole`
- Native: not yet (falls back)

## 9. Compiler architecture

```
source → lexer → parser → AST
                     ├→ gradual checker
                     ├→ interpreter (classes / try / import)
                     └→ C codegen (int unbox) → clang → binary
```

## 10. Builtins

`print`, `len`, `range`, `str`, `int`, `float`, `bool`, `list`, `dict`, `type`, `isinstance`, `sorted`, `min`, `max`, `sum`, `abs`, `enumerate`, `zip`, `open`, `input`, …

## Non-goals for v0.1

Self-hosting, full borrow checker, tracing GC, native classes, web/AI frameworks in-tree.
