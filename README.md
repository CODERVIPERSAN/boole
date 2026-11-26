# Boole

Python-like syntax. Gradual typing. Memory-safe runtime. Native speed via C.

Named after [George Boole](https://en.wikipedia.org/wiki/George_Boole) (1815–1864).

## Quick start

```bash
export PYTHONPATH=/home/sandy/boole   # or: pip install -e .
./bin/boole run examples/hello.boole
./bin/boole run --interp examples/classes.boole
./bin/boole check examples/typed.boole
./bin/boole test                      # 100 programs
./bin/boole bench                     # vs CPython
./bin/boole opt examples/switch.boole # which functions are typed / native
```

## Identity

| Item | Decision |
| --- | --- |
| Name | Boole |
| Extension | `.boole` |
| Command | `boole` |
| Manifest | `Boole.toml` (planned) |
| Spec | `docs/spec/v0.1/` + `PLAN.md` |
| Engine | `docs/engine/` (adaptive backends; contracts to this compiler) |

## What you get

- **Scripts like Python** — no types required
- **Production typing** — `static def` or `# boole: static`
- **Native by default** — Boole → C → `clang -O3 -flto`
- **Interpreter fallback** — edges the native backend rejects (e.g. some `sys` imports)
- **Memory safety** — refcounted runtime; you never call `free`
- **Execution engine (design)** — capability probe + backend selector in front of this compiler; see `docs/engine/`

```boole
# dynamic script
print("hi")
x = 1 + 2

# typed / optimizable
static def add(a: int, b: int) -> int:
    return a + b
```

## Proof

```text
boole test   → 100 passed, 0 failed
boole bench  → sum_loop ~1000× vs CPython (run time of built binary)
pytest       → engine + CLI tests
```

Hot loops win because ints stay unboxed in generated C. Compile time is separate (~0.3–0.4s with LTO); use `boole build` once, then run the binary.

## Commands

| Command | Purpose |
| --- | --- |
| `boole run file.boole` | native (auto-fallback to interp) |
| `boole run --interp …` | force interpreter |
| `boole build … -o out` | native binary |
| `boole check …` | type-check |
| `boole test` | run `tests/programs/*.boole` |
| `boole bench` | benchmarks vs Python |
| `boole opt …` | show static vs dynamic functions |

## Layout

```
boole/           # compiler (Python host) + engine.py contract
runtime/         # C runtime (refcounted values)
tests/programs/  # 100 language programs
benchmarks/
examples/
docs/spec/v0.1/  # language as-built
docs/engine/     # AI execution engine design
PLAN.md          # full single-shot plan
```

## Honest limits

Not self-hosting. Not an NL→binary product yet (that path is documented as a future engine backend). Not a replacement for every Rust/C++/Python ecosystem — a usable language core you can write scripts and typed modules in today, with an adaptive engine layer starting to contract to this compiler.
