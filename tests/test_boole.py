import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOLE = [sys.executable, "-m", "boole"]
ENV = {**dict(**__import__("os").environ), "PYTHONPATH": str(ROOT)}


def run(args, check=True):
    return subprocess.run(
        BOOLE + args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=check,
        env=ENV,
    )


def test_hello_native():
    r = run(["run", "--strict-native", "examples/hello.boole"])
    assert "Hello from Boole" in r.stdout
    assert "Hello, world!" in r.stdout


def test_script_native():
    r = run(["run", "--strict-native", "examples/script.boole"])
    assert "sum 1..5 = 15" in r.stdout
    assert "sorted = [1, 1, 3, 4, 5]" in r.stdout
    assert "max = 5" in r.stdout


def test_typed_native():
    r = run(["run", "--strict-native", "examples/typed.boole"])
    assert "5" in r.stdout
    assert "Hello, Boole" in r.stdout


def test_gradual():
    r = run(["run", "--strict-native", "examples/gradual.boole"])
    assert "ok" in r.stdout
    assert "42" in r.stdout
    assert "20" in r.stdout


def test_classes_interp():
    r = run(["run", "--interp", "examples/classes.boole"])
    assert "Point(4, 6)" in r.stdout


def test_check_typed():
    r = run(["check", "examples/typed.boole"])
    assert r.returncode == 0


def test_build():
    out = ROOT / "build" / "hello_bin"
    out.parent.mkdir(exist_ok=True)
    r = run(["build", "examples/hello.boole", "-o", str(out)])
    assert out.exists()
    got = subprocess.run([str(out)], capture_output=True, text=True, check=True)
    assert "Hello from Boole" in got.stdout


def test_programs_suite():
    r = run(["test"], check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "100 passed" in r.stdout


def test_opt_command():
    r = run(["opt", "examples/switch.boole"])
    assert r.returncode == 0
    assert "total" in r.stdout
