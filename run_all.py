import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_step(label: str, cmd: list[str]) -> None:
    print(f"\n==> {label}")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"Step failed: {label}")


def main() -> None:
    run_step(
        "Compile project",
        [
            sys.executable,
            "-m",
            "compileall",
            str(ROOT / "contract_negotiation_env"),
            str(ROOT / "tests"),
            str(ROOT / "benchmark_report.py"),
            str(ROOT / "showcase_run.py"),
            str(ROOT / "demo_run.py"),
        ],
    )
    run_step("Run unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"])
    run_step("Run benchmark report", [sys.executable, "benchmark_report.py"])
    run_step("Run showcase trajectory", [sys.executable, "showcase_run.py"])
    print("\nAll submission checks completed successfully.")


if __name__ == "__main__":
    main()
