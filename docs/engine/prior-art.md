# Prior art and competitor matrix (desk research)

**Status:** internal comparison for product positioning.  
**Not legal advice.** Licensing and patent notes are one-line desk-research flags only; do a real clearance before public claims or fundraising decks.

Goal: show where Boole + its AI execution engine sit relative to NL→code / adaptive compilation systems, without claiming “world’s first.”

---

## Summary table

| System | Input | Output | System discovery | Backend selection | Verification | Sandbox | Multi-lang | Production readiness | License / patent flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Prompt-to-Binary | NL / prompts | Binary / low-level | Limited | Model-driven | Research-level | Varies | Focused | Research | Check papers + code license |
| E2M | NL / specs | Machine-oriented code | Limited | Pipeline fixed | Research | Varies | Limited | Research | Check papers + code license |
| Stanford Agent JIT | Agent / task traces | JIT’d agent code paths | Runtime-aware | JIT policy | Partial | Agent sandbox often | Agent-centric | Research | Academic; check license |
| LaaC | Language-as-code / declarative | Executable artifacts | Tooling-dependent | Convention-based | Tooling-dependent | Optional | Often multi | Early product / research | Check project license |
| Verbose | Verbose / NL-ish specs | Code or programs | Limited | Fixed pipeline | Limited | Varies | Limited | Early | Check project license |
| clang / LLVM | C/C++/… | Object / binary | Target triple | Flags / LTO | Compilers + sanitizers | OS | Many frontends | Production | Apache-2.0-with-LLVM (typical) |
| CPython | Python | Bytecode → interp / JIT* | Limited | Single runtime | Language semantics | OS | Python | Production | PSF |
| AI coding assistants | NL + repo | Source patches | IDE / repo | Human picks compiler | Tests if user runs | IDE | Many | Product | Vendor ToS; not a compiler patent map |
| **Boole today** | `.boole` | C → clang binary / interp | clang + runtime probe | Native vs interp | Gradual checker | OS only | Boole | Usable core | Project license; no patent claim |
| **Boole engine target** | Boole + later NL / others | Binary / asm / adapters | Capability layer | Adaptive selector | Record + future sandbox | Planned | Planned | Design | Same; prior art dense in NL→code |

\*CPython JITs (e.g. experimental) do not change the “source → bytecode” product model.

---

## Rows in prose

### Prompt-to-Binary

- **Input:** natural language or structured prompts aimed at executable output.
- **Output:** binary or near-binary artifacts (research demos).
- **System / hardware discovery:** usually not a first-class portable capability layer.
- **Backend selection:** model or fixed demo pipeline, not a multi-backend selector with recorded policy.
- **Verification / sandbox:** research prototypes; not a production verifier+sandbox story.
- **Multi-language / readiness:** narrow demos; not a general language + engine product.
- **License / patent (desk):** treat papers and any released code as prior art for NL→binary claims; get counsel before “first to” marketing.

### E2M

- **Input:** English / high-level intent toward machine execution.
- **Output:** machine-oriented programs or binaries in research settings.
- **Discovery / selection / verify / sandbox:** typically fixed research pipeline rather than adaptive, system-aware selection.
- **Multi-language / readiness:** research.
- **License / patent (desk):** academic prior art for end-to-end NL→machine themes.

### Stanford Agent JIT

- **Input:** agent workflows / traces, not a general programming language.
- **Output:** JIT-style specialization of agent execution.
- **Discovery:** runtime-aware in the agent sense.
- **Backend selection:** JIT policy, not “Boole vs asm vs clang.”
- **Verification / sandbox:** often paired with agent isolation ideas; not a general binary verifier.
- **Multi-language / readiness:** agent research stack.
- **License / patent (desk):** academic; cite carefully; do not assume patent freedom.

### LaaC (Language as a Compiler / related “language as code” lines)

- **Input:** declarative or language-shaped specs.
- **Output:** executable artifacts via tooling.
- **Discovery / selection:** convention and plugin ecosystems more than ISA-aware asm emission.
- **Verification / sandbox:** depends on the concrete project.
- **Multi-language / readiness:** early product or research.
- **License / patent (desk):** check each named project; naming collisions possible.

### Verbose

- **Input:** verbose / NL-adjacent specifications.
- **Output:** generated programs.
- **Discovery / adaptive backends / verify / sandbox:** generally not the full combination Boole documents as a target.
- **Readiness:** early.
- **License / patent (desk):** project-specific.

### Conventional compilers (clang / LLVM)

- **Input:** high-level or IR (C, C++, Rust via llvm, etc.).
- **Output:** optimized native code; gold standard for codegen quality.
- **Discovery:** target triples, CPU features (`-march`), LTO/PGO.
- **Backend selection:** explicit user/toolchain flags, not NL tasks.
- **Verification:** compilers, linkers, sanitizers, tests — mature.
- **Sandbox:** OS / containers, not built into clang itself.
- **Multi-language / readiness:** production.
- **License / patent (desk):** LLVM license well understood; Boole already depends on `clang` as a backend driver.

### CPython and AI coding assistants

- **CPython:** language → bytecode → interpreter; not NL→a.out.
- **AI coding assistants:** NL → source diffs; the human (or CI) still runs a normal compiler. Strong product presence, weak claim to “adaptive verified multi-backend execution engine.”
- **License / patent (desk):** PSF / vendor ToS; assistants are prior art for NL→source, not for replacing assemblers.

---

## Boole today vs engine aim

| | Boole language (today) | Engine (aim) |
| --- | --- | --- |
| Input | `.boole` | `.boole` now; later NL and other languages |
| Path | AST → C → clang → binary (or interp) | Prefer adaptive choice; research path NL → asm → a.out **without** mandatory HLL script |
| Discovery | Implicit (clang must exist) | Explicit capability probe |
| Selection | Native else interp | Policy object + future backends |
| Verification | Gradual checker | Checker + recorded outcome; later sandbox |
| Differentiator to write down | Gradual + native speed | System awareness + backend selection + verification + multi-path execution |

**Positioning line (honest):** prior systems explore pieces of NL→code and agent JIT. Boole’s bet is the **combination**: a real language toolchain **plus** a system-aware engine that can choose Boole-native, interpreter, and eventually NL→assembly, with a verification record — not a slogan that no one else ever emitted a binary from English.

---

## What not to claim

- “World’s first AI compiler” or “first NL→binary.”
- That skipping high-level languages removes the need for IR, tests, or sandboxing.
- Patent non-infringement based on this document alone.
