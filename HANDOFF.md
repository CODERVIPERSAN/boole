# Handoff — Boole complete v1 core

## Done

1. Name **Boole** (Aethon rejected for trademark/name collisions).
2. Python-like gradual language: scripts + `static def` / `# boole: static`.
3. Native path: int-unboxing C codegen + `clang -O3 -flto`.
4. Interpreter: classes, inheritance, try/except, `.boole` imports, math/json/sys.
5. `boole test` — **100/100** programs passed.
6. `boole bench` — sum_loop ~1000×, range_sum ~800×, fib ~17× vs CPython run time.
7. Single plan: `PLAN.md`.

## Use

```bash
export PYTHONPATH=/home/sandy/boole
boole run file.boole
boole test
boole bench
```

## If a bench ever loses

1. Keep int locals unboxed (`_i` in generated C).
2. Keep `for x in range(...)` as a C for-loop.
3. Prefer `-O3 -flto` for release binaries; `-O1` is fine for `boole test`.
4. Avoid boxing in hot loops (don’t call `print` / build strings inside the timed loop).

## Still later (not blocking use)

- Native classes / try / import
- LLVM IR option
- `Boole.toml` + package manager
- Self-hosting
