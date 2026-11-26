# Boole AI execution engine — architecture

**Status:** design + first code contract (`boole.engine`).  
**Name:** Boole (not Aethon). Layer 2 sits in front of the Boole compiler; it does not replace the language.

## Thesis

A conventional stack is:

```
natural language → (human / LLM) → high-level language
    → compiler IR → assembly → assembler → machine code → run
```

The engine’s **research target** is to collapse the high-level-language step when the host architecture is known:

```
natural language + known ISA / ABI / OS
    → assembly (or object code)
    → assembler / linker → a.out (or ELF binary)
    → execute
```

That is **not** “another English-to-Python/C compiler.” Intermediate `.py` / `.c` / `.boole` scripts are an optional path, not a required one. Training / adaptation that maps task → machine code (or asm) end-to-end is the long-term model; verification and sandboxing remain mandatory before execution.

Today’s shipping path remains honest:

```
.boole → Boole frontend → C codegen → clang → binary
```

Natural-language intake is live via `boole nl-asm`: the LLM reads `boole/asm_rules.txt`,
emits GAS, then `clang -nostdlib -static` runs the binary. Edit that rulebook to teach the model;
do not add Python phrase matchers for every language the user might type.

## Layers

| Layer | Role |
| --- | --- |
| Boole language | Production-grade gradual language; see `docs/spec/v0.1/` |
| AI execution engine | Capability discovery, task IR, backend selection, verification record |

```
Task
  → capability discovery
  → backend selector
       ├─ boole_native   (build_native / run_native)     [implemented]
       ├─ boole_interp   (interpreter fallback)          [implemented]
       ├─ nl_asm         (NL → asm → a.out)              [planned]
       ├─ foreign_lang   (other HLLs via adapters)       [planned]
       └─ wasm / agent   (later)                         [planned]
  → verification record
```

## Capability discovery

Probe only what the first backends need:

| Probe | Purpose |
| --- | --- |
| `clang` on `PATH` | Native Boole compile |
| `runtime/boole_rt.c` (+ OOP) present | Link Boole runtime |
| Interpreter importable | Fallback when native rejects a construct |
| Host arch / OS (uname) | Recorded for future `nl_asm`; not used to emit asm yet |
| Assembler (`as` / `clang -c`) | Future NL→asm path |

No deep hardware inventory, MCP, or GPU discovery in this slice.

## Task representation

```text
Task:
  language   : "boole" | other string | "nl" (future)
  source     : text
  path       : optional path hint (e.g. file.boole)
  mode       : "run" | "binary"
  check      : bool  (run gradual checker when applicable)
```

- **Accepted now:** `language == "boole"` (or path ending in `.boole`).
- **Rejected now:** other languages and natural language → structured `no_backend` (does not invoke clang).
- Natural language is a **future input kind**, not part of the first importable contract.

## Backend selector

1. Discover capabilities.
2. If task is Boole and clang + runtime are available → `boole_native`.
3. If native fails with the existing “unsupported / use interpreter” contract → `boole_interp` (same policy as `cmd_run`, unless strict).
4. Otherwise → `no_backend` with a reason string.

Selector does **not** invent a second codegen path. Native work calls existing `boole.native.build_native` / `run_native`.

## Contract to current compiler

| Engine piece | Existing module |
| --- | --- |
| Parse / check | `boole.parser`, `boole.checker` |
| Native binary | `boole.native.build_native` |
| Native run | `boole.native.run_native` |
| Interp fallback | `boole.interpreter.interpret` |

Code lives in `boole/engine.py`. No new CLI subcommand in this slice; the contract is importable and unit-tested.

## Verifier (this slice)

- Optional typecheck via `boole.checker.check` when `task.check` or the program is static.
- Result: `VerificationRecord` with `ok: bool`, `backend: str`, `notes: list[str]`.
- **Not in this slice:** sandbox, supply-chain policy, MCP, result cache, scheduler.

## Planned: NL → assembly → a.out

When implemented, the `nl_asm` backend will:

1. Read host ISA / ABI / OS from discovery.
2. Emit assembly (or object code) for that target **without** requiring a generated high-level script.
3. Assemble/link with the system assembler (or `clang` as driver) to an `a.out` / ELF binary.
4. Record verification (syntax of asm, link success, optional smoke run under a future sandbox).

Risks to keep explicit in docs and product claims:

- Correctness of model-emitted asm is hard; verification is not optional.
- Prior systems already explore NL→binary; see `docs/engine/prior-art.md`.
- Skipping HLL does not skip the need for an IR *inside* the engine (task IR, capability record, verification record still exist).

## Out of scope (this slice)

- LLM weights / training loop
- Sandbox, MCP, cache, multi-language frontends
- Renaming to Aethon
- Claiming Boole is the first NL→binary system
