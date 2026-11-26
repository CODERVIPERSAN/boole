"""NL → LLM (with rulebook) → GAS → clang → run.

No high-level language in the middle. Rules live in asm_rules.txt for the model,
not as Python phrase matchers.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent / "asm_rules.txt"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def _nvidia_env() -> dict[str, str]:
    """Force NVIDIA device 0 for Ollama/CUDA generation."""
    env = os.environ.copy()
    env.setdefault("CUDA_VISIBLE_DEVICES", "0")
    env.setdefault("OLLAMA_NUM_GPU", "999")  # offload as many layers as VRAM allows
    return env


def gpu_status() -> str:
    """Short status string: ollama processor + nvidia-smi if present."""
    bits: list[str] = []
    try:
        proc = subprocess.run(
            ["ollama", "ps"],
            capture_output=True,
            text=True,
            timeout=5,
            env=_nvidia_env(),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            bits.append(proc.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.TimeoutExpired):
        pass
    if shutil.which("nvidia-smi"):
        try:
            proc = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.used",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                bits.append("nvidia-smi: " + proc.stdout.strip())
        except (OSError, subprocess.TimeoutExpired):
            pass
    return " | ".join(bits) if bits else "GPU status unknown"


@dataclass
class AsmRunResult:
    ok: bool
    asm: str
    stdout: str
    stderr: str
    exit_code: int | None
    binary_path: str | None = None
    notes: list[str] | None = None


def load_asm_rules() -> str:
    if RULES_PATH.exists():
        return RULES_PATH.read_text(encoding="utf-8")
    return "Emit x86_64 Linux GAS freestanding _start; write=1 exit=60; ```asm only."


def _fixup_gas(asm: str) -> str:
    """Tiny mechanical ABI/syntax fixes — does not reinterpret the user's message text."""
    asm = re.sub(
        r"\bmov\s+msg_len\s*,\s*%rdx\b",
        "mov     $msg_len, %rdx",
        asm,
        flags=re.IGNORECASE,
    )
    # Classic LLM bug: mov $1,%rax (write) then xor %rdi,%rdi (fd=0). Force stdout.
    asm = re.sub(
        r"(mov\s+\$1,\s*%rax\b.*?)\nxor\s+%rdi,\s*%rdi",
        r"\1\n        mov     $1, %rdi",
        asm,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # GAS .ascii requires double quotes, not single quotes
    asm = re.sub(
        r"\.ascii\s+'([^']*)'",
        lambda m: '.ascii  "' + m.group(1).replace('"', '\\"') + '"',
        asm,
    )
    asm = re.sub(
        r"\.asciz\s+'([^']*)'",
        lambda m: '.asciz  "' + m.group(1).replace('"', '\\"') + '"',
        asm,
    )
    # Drop junk labels LLMs invent
    lines = [ln for ln in asm.splitlines() if not re.match(r"\s*\.globl\s+msg_len\b", ln)]
    asm = "\n".join(lines) + "\n"
    if ".global _start" not in asm and ".globl _start" not in asm:
        asm = "        .global _start\n" + asm
    return asm


def _asm_preflight(asm: str) -> str | None:
    """Return a repair hint if the program is incomplete, else None."""
    starts = re.findall(r"(?m)^\s*_start\s*:", asm)
    if len(starts) > 1:
        return (
            "DUPLICATE _start: define _start exactly once. "
            "Put write syscall and exit syscall in the SAME _start, then .rodata."
        )
    uses_msg = bool(re.search(r"\bmsg\b", asm))
    has_msg_label = bool(re.search(r"(?m)^msg\s*:", asm))
    has_len = bool(re.search(r"(?m)\.equ\s+msg_len\b", asm))
    if uses_msg and not has_msg_label:
        return (
            "UNDEFINED msg: you referenced msg / msg_len but omitted the data.\n"
            "You MUST end the program with:\n"
            "        .section .rodata\n"
            "msg:\n"
            '        .ascii  "text here\\n"\n'
            "        .equ    msg_len, . - msg\n"
            "Use DOUBLE quotes for .ascii, never single quotes."
        )
    if has_msg_label and not has_len and re.search(r"\$msg_len", asm):
        return "Add `.equ msg_len, . - msg` immediately after the .ascii line."
    if re.search(r"\.ascii\s+'", asm):
        return 'Replace .ascii \'...\' with .ascii "..." (double quotes only).'
    # write path must load %rax with 1 before the first syscall when printing
    if has_msg_label and not re.search(r"mov\s+\$1,\s*%rax", asm, flags=re.I):
        return "Before write syscall set: mov $1, %rax   then mov $1, %rdi ; lea msg(%rip), %rsi ; mov $msg_len, %rdx ; syscall"
    return None


def extract_assembly(text: str) -> str:
    """Pull GAS from LLM output; prefer fenced asm blocks."""
    fences = re.findall(
        r"```(?:asm|gas|nasm|s|assembly)?\s*\n(.*?)```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if fences:
        for block in fences:
            if "_start" in block or ".global" in block or ".globl" in block:
                return _fixup_gas(block.strip() + "\n")
        return _fixup_gas(fences[0].strip() + "\n")

    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith(".") or s.startswith("_start") or s.startswith("main:"):
            start = i
            break
    if start is None:
        raise ValueError("no assembly found (need ```asm fence with _start)")
    return _fixup_gas("\n".join(lines[start:]).strip() + "\n")


def assemble_and_run(
    asm: str,
    *,
    out_bin: Path | None = None,
    keep_s: Path | None = None,
    run: bool = True,
) -> AsmRunResult:
    """Write .s, clang -nostdlib -static, optionally execute."""
    notes: list[str] = []
    if shutil.which("clang") is None:
        return AsmRunResult(False, asm, "", "clang not found", None, notes=["no clang"])

    cleanup_bin = out_bin is None
    if out_bin is None:
        fd, name = tempfile.mkstemp(prefix="boole_asm_", suffix=".bin")
        os.close(fd)
        out_bin = Path(name)

    if keep_s is not None:
        keep_s.write_text(asm, encoding="utf-8")
        s_file = keep_s
        cleanup_s = False
    else:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".s", delete=False, encoding="utf-8")
        tmp.write(asm)
        tmp.close()
        s_file = Path(tmp.name)
        cleanup_s = True

    cmd = ["clang", "-nostdlib", "-static", "-o", str(out_bin), str(s_file)]
    notes.append(" ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return AsmRunResult(
                False,
                asm,
                proc.stdout or "",
                proc.stderr or "clang failed",
                proc.returncode,
                notes=notes,
            )
        os.chmod(out_bin, 0o755)
        if not run:
            return AsmRunResult(True, asm, "", "", 0, str(out_bin), notes=notes)

        run_proc = subprocess.run([str(out_bin)], capture_output=True, text=True)
        return AsmRunResult(
            True,
            asm,
            run_proc.stdout or "",
            run_proc.stderr or "",
            run_proc.returncode,
            str(out_bin),
            notes=notes,
        )
    finally:
        if cleanup_s:
            try:
                os.unlink(s_file)
            except OSError:
                pass
        if cleanup_bin and run:
            try:
                os.unlink(out_bin)
            except OSError:
                pass


def _llm_via_http(model: str, full: str, *, timeout: int = 180) -> str:
    """Generate on the Ollama server (keeps model resident on NVIDIA GPU)."""
    body = json.dumps(
        {
            "model": model,
            "prompt": full,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                # Keep generation deterministic-ish for asm
                "temperature": 0.1,
                "num_predict": 512,
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data.get("response") or ""
    if not text.strip():
        raise RuntimeError("ollama HTTP returned empty response")
    return text


def _llm_via_cli(model: str, full: str, *, timeout: int = 180) -> str:
    """Fallback: ollama CLI with CUDA_VISIBLE_DEVICES=0."""
    if shutil.which("ollama") is None:
        raise RuntimeError("ollama not found on PATH")
    proc = subprocess.run(
        ["ollama", "run", model, full],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_nvidia_env(),
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "ollama failed")
    return proc.stdout


def llm_assembly(
    prompt: str,
    *,
    model: str = "llama3.2",
    repair_hint: str | None = None,
    rules: str | None = None,
) -> str:
    """Ask Ollama for GAS using the rulebook — prefer GPU-resident HTTP API."""
    rulebook = rules if rules is not None else load_asm_rules()
    user = (
        "USER TASK (understand intent freely; emit assembly only):\n"
        f"{prompt}\n"
    )
    if repair_hint:
        user += (
            "\nASSEMBLER ERRORS — fix the program and output a full corrected ```asm block:\n"
            f"{repair_hint}\n"
        )
    full = f"{rulebook}\n\n---\n\n{user}"
    # Prefer HTTP so the model stays on the NVIDIA GPU across fuzz cases
    try:
        return _llm_via_http(model, full)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError, json.JSONDecodeError):
        return _llm_via_cli(model, full)


def nl_to_binary_run(
    prompt: str,
    *,
    model: str = "llama3.2",
    emit_s: Path | None = None,
    retries: int = 1,
    llm_asm: bool = True,
) -> AsmRunResult:
    """NL → LLM (rulebook) → asm → clang → run. Straight path, no phrase templates.

    Retries only if clang rejects the assembly (feeds errors back to the model once).
    Does not gate on English/Tamil/Java regex rules.
    """
    del llm_asm  # always LLM-first; kept for CLI compatibility
    hint: str | None = None
    last: AsmRunResult | None = None
    for attempt in range(retries + 1):
        raw = llm_assembly(prompt, model=model, repair_hint=hint)
        try:
            asm = extract_assembly(raw)
        except ValueError as err:
            hint = f"{err}\nModel output was:\n{raw[:2000]}"
            last = AsmRunResult(False, raw, "", str(err), 1, notes=[f"extract failed attempt {attempt}"])
            continue
        pre = _asm_preflight(asm)
        if pre:
            hint = pre + "\n\nYour previous asm:\n" + asm
            last = AsmRunResult(False, asm, "", pre, 1, notes=[f"preflight attempt {attempt}"])
            continue
        result = assemble_and_run(asm, keep_s=emit_s, run=True)
        result.notes = (result.notes or []) + [f"llm attempt {attempt + 1}"]
        if result.ok:
            return result
        # Enrich clang/ld errors for the next LLM repair
        err = result.stderr or "assemble failed"
        if "msg" in err and "undefined reference" in err:
            err += (
                "\nFIX: append .section .rodata / msg: / .ascii \"...\\n\" / "
                ".equ msg_len, . - msg  (double quotes)."
            )
        if "expected string" in err:
            err += '\nFIX: .ascii must use double quotes: .ascii "text\\n"'
        hint = err
        last = result
    assert last is not None
    return last
