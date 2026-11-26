# Boole

Python-like language with gradual typing and native speed — plus an AI path that turns natural language into assembly and runs it.

Named after [George Boole](https://en.wikipedia.org/wiki/George_Boole) (1815–1864).

## Quick start

```bash
cd ~/boole
export PYTHONPATH=.

# Language
./bin/boole run examples/hello.boole
./bin/boole test                      # 100 programs
./bin/boole bench                     # vs CPython

# Natural language → assembly → binary (needs Ollama + clang; uses NVIDIA GPU if available)
python -m boole nl-asm "echo hello"
python -m boole nl-asm "System.out.println('poda dai')"
python -m boole nl-asm "hello print pannu"
python -m boole nl-asm --show-asm "Print: hi"
```

From any directory (repo-root `__main__.py` fixes the `~/boole` name clash):

```bash
python -m boole nl-asm 'print("hello from natural language")'
```

## Two layers

| Layer | What it is |
| --- | --- |
| **Boole language** | `.boole` → gradual checker → C → `clang -O3 -flto` (or interpreter) |
| **AI execution engine** | Task + capability probe + backends; `nl-asm` is NL → LLM (rulebook) → GAS → clang → run |

Docs: [`docs/spec/v0.1/`](docs/spec/v0.1/) (language) · [`docs/engine/`](docs/engine/) (engine + prior art) · [`PLAN.md`](PLAN.md)

## Identity

| Item | Decision |
| --- | --- |
| Name | Boole |
| Extension | `.boole` |
| Command | `boole` / `python -m boole` |
| Manifest | `Boole.toml` (planned) |
| NL→asm rules | [`boole/asm_rules.txt`](boole/asm_rules.txt) (edit this to teach the model) |

## Language

- Scripts like Python — types optional
- Production typing — `static def` or `# boole: static`
- Native by default — Boole → C → clang
- Interpreter fallback for unsupported edges
- Memory-safe refcounted runtime

```boole
print("hi")
x = 1 + 2

static def add(a: int, b: int) -> int:
    return a + b
```

## Natural language → machine code

No high-level script in the middle on this path:

```text
your sentence → Ollama (GPU) + asm_rules.txt → .s → clang -nostdlib -static → run
```

```bash
python -m boole nl-asm "please try to print the word 'poda dai'"
python -m boole asm-run examples/asm/hello.s          # pipe/file GAS → run
cat examples/asm/hello.s | python -m boole asm-run
```

Prefer single quotes around the whole prompt when it contains `"..."`.

## Commands

| Command | Purpose |
| --- | --- |
| `boole run file.boole` | native compile + run (interp fallback) |
| `boole build -o out` | emit native binary |
| `boole check` / `opt` / `test` / `bench` | type-check, report, proof suite |
| `boole nl-asm "…"` | NL → LLM → assembly → run |
| `boole asm-run [file.s]` | assemble + run GAS (stdin OK) |

## Proof

```text
boole test                          → 100 passed
boole bench                         → hot loops ≫ CPython run time
pytest                              → engine + CLI tests
benchmarks/nl_print_fuzz.py --count 1000
  → last run ~70% pass on crazy print phrasings (LLM quality bound)
```

## Layout

```
boole/            # compiler + engine.py + asm_run.py + asm_rules.txt
runtime/          # C runtime
tests/programs/   # 100 language programs
examples/asm/     # freestanding GAS hello
docs/spec/v0.1/   # language as-built
docs/engine/      # architecture + prior-art matrix
benchmarks/       # microbenches + nl_print_fuzz.py
```

## Honest limits

- Not self-hosting; not a full Rust/C++/Python replacement.
- `nl-asm` depends on **Ollama** (e.g. `llama3.2`) and **clang**; GPU speeds generation, not assemble/run.
- Small models still mis-emit asm sometimes — fix by editing `asm_rules.txt`, raising `--retries`, or using a stronger `--model`.
- Do not claim “world’s first” NL→binary; see `docs/engine/prior-art.md`.
