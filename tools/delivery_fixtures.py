#!/usr/bin/env python3
"""Host smoke fixtures for delivery-check; does not create an active Change."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "harness" / "fixtures" / "delivery-check"


def run(tasks: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "delivery_check.py"),
            "--change",
            "fixture-native",
            "--tasks",
            tasks,
            "--validate-json",
            str(FIXTURE / "validate.json"),
            "--apply-json",
            str(FIXTURE / "apply.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def main() -> int:
    positive = run("harness/fixtures/delivery-check/tasks-positive.md")
    if positive.returncode != 0:
        print(positive.stdout)
        print(positive.stderr, file=sys.stderr)
        return 1
    negative = run("harness/fixtures/delivery-check/tasks-negative-zero.md")
    if negative.returncode == 0:
        print("negative 0-task fixture unexpectedly passed", file=sys.stderr)
        return 1
    print("PASS delivery-check fixtures: positive=0, zero-tasks!=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
