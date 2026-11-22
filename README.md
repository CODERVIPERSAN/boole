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

## What you get

- **Scripts like Python** — no types required
- **Production typing** — `static def` or `# boole: static`
- **Native by default** — Boole → C → `clang -O3 -flto`
- **Interpreter fallback** — classes, `try`/`except`, imports
- **Memory safety** — refcounted runtime; you never call `free`

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
pytest       → 11 passed
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
boole/           # compiler (Python host)
runtime/         # C runtime (refcounted values)
tests/programs/  # 100 language programs
benchmarks/
examples/
docs/spec/v0.1/
PLAN.md          # full single-shot plan
```

## Honest limits

Not self-hosting. Native backend does not yet emit classes/`try`/imports (falls back to interp). Not a replacement for every Rust/C++/Python ecosystem — a usable language core you can write scripts and typed modules in today.
