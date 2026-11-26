#!/usr/bin/env python3
"""Fuzz 1000 crazy NL print prompts through boole nl-asm (LLM → asm → run).

Shows a live tqdm progress bar. Writes JSONL results as it goes.

  PYTHONPATH=. python benchmarks/nl_print_fuzz.py
  PYTHONPATH=. python benchmarks/nl_print_fuzz.py --limit 20
  PYTHONPATH=. python benchmarks/nl_print_fuzz.py --count 1000 --retries 1
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from boole.asm_run import nl_to_binary_run  # noqa: E402

WORDS = [
    "hello", "world", "poda", "dai", "boole", "asm", "tamil", "pannu", "sonnan",
    "alpha", "beta", "gamma", "delta", "omega", "nova", "pixel", "quantum",
    "coffee", "kernel", "syscall", "clang", "gas", "linux", "x86", "ripp",
    "vanakkam", "nandri", "epdi", "iruka", "machan", "da", "ya", "bro",
]

TEMPLATES = [
    # (prompt_fmt, note) — {m} = message payload
    ('print("{m}")', "python-dquote"),
    ("print('{m}')", "python-squote"),
    ("print({m})", "python-bare"),
    ('System.out.println("{m}")', "java-dquote"),
    ("System.out.println('{m}')", "java-squote"),
    ("System.out.println({m});", "java-bare-semi"),
    ("echo {m}", "echo-bare"),
    ("echo '{m}'", "echo-squote"),
    ('echo "{m}"', "echo-dquote"),
    ("Print: {m}", "print-colon"),
    ("Print exactly: {m}", "print-exactly"),
    ("please print {m}", "please-print"),
    ("please try to print the word '{m}'", "please-word"),
    ('please try to print the word "{m}"', "please-word-dq"),
    ("say '{m}'", "say"),
    ('say "{m}"', "say-dq"),
    ("write '{m}'", "write"),
    ("{m} print pannu", "tamil-pannu"),
    ("{m} print pannu tamil la sonnan da", "tamil-long"),
    ("can you print {m} for me", "can-you"),
    ("display the text {m}", "display"),
    ("output {m} to stdout", "stdout"),
    ("log('{m}')", "log"),
    ("console.log('{m}')", "console-log"),
    ("puts '{m}'", "puts"),
    ("printf {m}", "printf"),
    ("I want you to print {m}", "want"),
    ("kindly print '{m}' now", "kindly"),
    ("print out: {m}", "print-out"),
    ("show me {m}", "show-me"),
]


def make_message(i: int, rng: random.Random) -> str:
    """Build a short printable payload (no quotes/backslashes)."""
    n = 1 + (i % 4)
    parts = [rng.choice(WORDS) for _ in range(n)]
    if i % 7 == 0:
        parts.append(str(i))
    if i % 11 == 0:
        parts.append("OK")
    return " ".join(parts)


def generate_cases(count: int, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    cases = []
    for i in range(count):
        msg = make_message(i, rng)
        tmpl, kind = TEMPLATES[i % len(TEMPLATES)]
        # Extra chaos every few cases
        prompt = tmpl.format(m=msg)
        if i % 13 == 0:
            prompt = prompt + "   "
        if i % 17 == 0:
            prompt = "  " + prompt
        if i % 19 == 0 and kind.startswith("python"):
            prompt = prompt.replace("print", "Print", 1)
        cases.append(
            {
                "id": i,
                "prompt": prompt,
                "expected": msg,
                "kind": kind,
            }
        )
    return cases


def normalize_out(s: str) -> str:
    return (s or "").replace("\x00", "").strip()


def bar_line(done: int, total: int, passed: int, failed: int, width: int = 30) -> str:
    filled = int(width * done / total) if total else width
    return (
        f"|{'█' * filled}{'░' * (width - filled)}| "
        f"{done}/{total} ({100 * done // total if total else 0}%) "
        f"pass={passed} fail={failed}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Fuzz NL print → asm → run")
    ap.add_argument("--count", type=int, default=1000, help="number of cases (default 1000)")
    ap.add_argument("--limit", type=int, default=0, help="stop after N cases (0 = all)")
    ap.add_argument("--offset", type=int, default=0, help="skip first N cases")
    ap.add_argument("--model", default="llama3.2")
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--out",
        default=str(ROOT / "benchmarks" / "nl_print_fuzz_results.jsonl"),
        help="JSONL results path",
    )
    ap.add_argument(
        "--progress-file",
        default=str(ROOT / "benchmarks" / "nl_print_fuzz_progress.txt"),
        help="single-line progress file for watchers",
    )
    args = ap.parse_args()

    cases = generate_cases(args.count, seed=args.seed)
    if args.offset:
        cases = cases[args.offset :]
    if args.limit and args.limit > 0:
        cases = cases[: args.limit]

    out_path = Path(args.out)
    prog_path = Path(args.progress_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Fresh run truncates results
    out_path.write_text("", encoding="utf-8")

    passed = failed = 0
    t0 = time.time()
    total = len(cases)

    with tqdm(
        cases,
        total=total,
        desc="nl-print fuzz",
        unit="case",
        dynamic_ncols=True,
        mininterval=0.5,
    ) as bar:
        for case in bar:
            t1 = time.time()
            ok = False
            got = ""
            err = ""
            try:
                result = nl_to_binary_run(
                    case["prompt"],
                    model=args.model,
                    retries=args.retries,
                )
                got = normalize_out(result.stdout)
                exp = case["expected"]
                ok = bool(result.ok) and got == exp
                if not ok:
                    err = result.stderr or f"got={got!r} expected={exp!r}"
            except Exception as exc:  # noqa: BLE001 — fuzz harness
                err = str(exc)

            if ok:
                passed += 1
            else:
                failed += 1

            rec = {
                **case,
                "ok": ok,
                "got": got,
                "error": err[:500],
                "seconds": round(time.time() - t1, 2),
            }
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            done = passed + failed
            line = bar_line(done, total, passed, failed)
            prog_path.write_text(
                line
                + f" elapsed={time.time() - t0:.0f}s"
                + f" last_id={case['id']} last_ok={ok}\n",
                encoding="utf-8",
            )
            bar.set_postfix(pass_=passed, fail=failed, refresh=False)
            # Also print a clean progress line periodically for non-TTY logs
            if done == total or done % 5 == 0 or not ok:
                tqdm.write(line)

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(100.0 * passed / total, 2) if total else 0.0,
        "elapsed_sec": round(time.time() - t0, 1),
        "results": str(out_path),
    }
    summary_path = out_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
