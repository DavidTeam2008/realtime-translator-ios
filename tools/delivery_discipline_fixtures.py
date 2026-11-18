#!/usr/bin/env python3
"""Hermetic discipline-receipt fixtures for the vendored v0.3.1 gate."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "tools" / "vendor"
SUPERPOWERS_VERSION = "v7.0.2"
SUPERPOWERS_COMMIT = "22f0b463e7a5e579904dd6211a520321035526f7"


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(f"fixture git {' '.join(args)} failed: {completed.stderr}")
    return completed.stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_verify(root: Path, receipt: Path, base: str, head: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(VENDOR)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_delivery_toolchain.discipline_cli",
            "verify",
            "--root",
            str(root),
            "--receipt",
            str(receipt),
            "--change",
            "fixture-discipline",
            "--task",
            "1",
            "--base",
            base,
            "--head",
            head,
            "--evidence",
            "fixture-evidence",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="discipline-fixture-") as raw:
        root = Path(raw)
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "fixture@example.invalid")
        _git(root, "config", "user.name", "fixture")
        _write(root / "README.md", "fixture base\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "base")
        base = _git(root, "rev-parse", "HEAD")

        discipline_dir = root / "harness" / "evidence" / "discipline" / "fixture-discipline"
        red_log = discipline_dir / "task-1-red.log"
        green_log = discipline_dir / "task-1-green.log"
        _write(red_log, "command: fixture-test\nEXIT_CODE=1\n")
        _git(root, "add", "harness/evidence/discipline/fixture-discipline/task-1-red.log")
        _git(root, "commit", "-qm", "red")
        red_commit = _git(root, "rev-parse", "HEAD")

        _write(green_log, "command: fixture-test\nEXIT_CODE=0\n")
        _git(root, "add", "harness/evidence/discipline/fixture-discipline/task-1-green.log")
        _git(root, "commit", "-qm", "green")
        green_commit = _git(root, "rev-parse", "HEAD")

        receipt = discipline_dir / "task-1.json"
        receipt_doc = {
            "schemaVersion": 1,
            "kind": "superpowers-discipline-receipt",
            "change": "fixture-discipline",
            "task": 1,
            "base": base,
            "head": green_commit,
            "discipline": {
                "name": "superpowers",
                "version": SUPERPOWERS_VERSION,
                "commit": SUPERPOWERS_COMMIT,
            },
            "tdd": {
                "red": {
                    "commit": red_commit,
                    "command": "fixture-test",
                    "exitCode": 1,
                    "artifact": "harness/evidence/discipline/fixture-discipline/task-1-red.log",
                    "sha256": _sha256(red_log),
                },
                "green": {
                    "commit": green_commit,
                    "command": "fixture-test",
                    "exitCode": 0,
                    "artifact": "harness/evidence/discipline/fixture-discipline/task-1-green.log",
                    "sha256": _sha256(green_log),
                },
            },
            "debugging": {"rootCause": "fixture root cause"},
            "verification": {"evidenceIds": ["fixture-evidence"]},
        }
        _write(receipt, json.dumps(receipt_doc, ensure_ascii=False, indent=2) + "\n")
        _git(root, "add", "harness/evidence/discipline/fixture-discipline/task-1.json")
        _git(root, "commit", "-qm", "receipt")
        positive = _run_verify(root, receipt, base, green_commit)
        if positive.returncode != 0:
            print("[FAIL] discipline positive fixture failed")
            print(positive.stdout)
            print(positive.stderr, file=sys.stderr)
            return 1

        red_log.write_text("command: fixture-test\nEXIT_CODE=0\n", encoding="utf-8")
        negative = _run_verify(root, receipt, base, green_commit)
        if negative.returncode == 0:
            print("[FAIL] discipline tampered fixture unexpectedly passed", file=sys.stderr)
            return 1
        print("PASS discipline fixtures: positive=0, tampered!=0")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
