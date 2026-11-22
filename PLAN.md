# Boole — single checklist plan

**Keep in sync with `list.md`.**  
When you add a task → add it in **both** files.  
When you finish a task → tick it in **both** files (`[x]`).

Architecture (current):

```
.boole → lexer → parser → AST
              → gradual checker
              → native: C codegen → clang -O3 -flto
              → interp: leftover edges (e.g. sys); classes/try/import are native
```

Legend: `[x]` done · `[ ]` todo

---

## 0. Product decisions (fixed)

- [x] Name: **Boole** (`.boole`, command `boole`)
- [x] Syntax: Python-like
- [x] Typing: gradual (scripts + `static def` / `# boole: static`)
- [x] Default run: native C + clang; `--interp` for unsupported edges
- [x] Proof bar: `boole test` (~100 programs) + `boole bench`

---

## 1. v1 core (shipped)

- [x] Lexer → parser → AST
- [x] Gradual type checker
- [x] Interpreter (scripts, classes, try, import)
- [x] Native codegen (Boole → C → clang)
- [x] Refcounted memory-safe runtime
- [x] Int unboxing + `range` for-loops
- [x] Lists, dicts, f-strings, functions
- [x] CLI: `run`, `build`, `check`, `opt`, `test`, `bench`, `lex`, `parse`
- [x] ~100 programs passing
- [x] Hot-loop benches ahead of CPython

---

## 2. Next — stop being a toy (priority)

- [x] Native classes + inheritance (no interp fallback)
- [x] Native try / except / finally
- [x] Native modules / import
- [ ] Better errors (file:line + hints)
- [ ] `boole fmt`
- [ ] Align folders: fill or remove empty `compiler/`
- [ ] Full written language spec v0.1

---

## 3. Near Python (ecosystem)

- [ ] Real `std/` (fs, path, process, regex, json, http, time, random, test)
- [ ] `Boole.toml` + `boole pkg`
- [ ] Package registry
- [ ] C FFI
- [ ] Python FFI (NumPy / PyTorch bridge)
- [ ] REPL
- [ ] Docs + “Python → Boole” tutorial
- [ ] 3 killer libraries

---

## 4. Near Rust (safe systems)

- [ ] Unique-by-default + `Rc` + `defer` + `unsafe`
- [ ] `task` concurrency (no shared-memory data races)
- [ ] `no_runtime` / embedded subset
- [ ] Enums + exhaustive matching
- [ ] Workspaces + lockfile
- [ ] Sanitizer-friendly / unsafe audit story
- [ ] Cross-compile Linux / macOS / Windows

---

## 5. Near C++ (speed + control)

- [ ] LLVM IR backend
- [ ] Debug info (gdb/lldb)
- [ ] Documented LTO / PGO release profile
- [ ] Zero-cost generics (monomorphize)
- [ ] No-hidden-alloc hot-path mode
- [ ] C/C++ ABI bridge
- [ ] SIMD / vector helpers
- [ ] Real benches vs C++/Rust (not only micro-loops)

---

## 6. Trust & release

- [ ] CI (test + bench smoke)
- [ ] Semver + compatibility policy
- [ ] Package supply-chain / security policy
- [ ] Trademark + domain clearance
- [ ] Self-hosting compiler (long-term)

---

## How to use this plan

1. Pick the next unchecked item in **§2**, then **§3**.
2. Implement + prove with tests/benches.
3. Tick the box here **and** in `list.md`.
4. New ideas → new checkbox in **both** files under the right section.
