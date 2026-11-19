#!/usr/bin/env python3
"""Hermetic smoke fixtures for the host delivery-check adapter.

Each fixture runs in a throwaway git repository with its own minimal host
profile, so the result does not depend on this repository's history, scope,
or deny patterns.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "harness" / "fixtures" / "delivery-check"
TOOLS = ROOT / "tools"
VENDOR_SRC = TOOLS / "vendor" / "ai_delivery_toolchain"


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise SystemExit(f"fixture git {' '.join(args)} failed: {completed.stderr}")
    return completed.stdout.strip()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _profile(discipline_required: bool = False, contract_lint_required: bool = False) -> dict:
    delivery = {"ci": {"required": False, "reason": "hermetic fixture"}}
    if discipline_required:
        delivery["discipline"] = {"required": True, "dir": "harness/evidence/discipline"}
    if contract_lint_required:
        delivery["contractLint"] = {"required": True, "profile": "strict"}
    return {
        "paths": {"evidence": "harness/evidence"},
        "claims": [],
        "delivery": delivery,
    }


def _prepare_repo(
    root: Path, discipline_required: bool = False, contract_lint_required: bool = False
) -> str:
    shutil.copytree(VENDOR_SRC, root / "tools" / "vendor" / "ai_delivery_toolchain")
    for cache in (root / "tools" / "vendor").rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    _write(root / "tools" / "openspec", "#!/bin/sh\nexit 1\n")
    (root / "tools" / "openspec").chmod(0o755)
    _write(
        root / "harness" / "config.json",
        json.dumps(_profile(discipline_required, contract_lint_required), ensure_ascii=False, indent=2),
    )
    _write(root / "harness" / "test-baseline.json", "{}\n")
    (root / "harness" / "evidence").mkdir(parents=True, exist_ok=True)
    change_dir = root / "openspec" / "changes" / "fixture-native"
    _write(change_dir / "proposal.md", "# Proposal\n")
    _write(change_dir / "design.md", "# Design\n")
    _write(change_dir / "specs" / "core" / "spec.md", "# Spec\n")
    _write(change_dir / "tasks.md", "# Delivery Contract\n")

    _git(root, "init", "-q")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "fixture")
    _write(root / "README.md", "fixture base\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "fixture base")
    return _git(root, "rev-parse", "HEAD")


def _run_case(
    name: str,
    expect_ok: bool,
    discipline_required: bool = False,
    contract_lint_required: bool = False,
    expect_message: str | None = None,
) -> None:
    with tempfile.TemporaryDirectory(prefix="delivery-fixture-") as tmp_raw:
        tmp = Path(tmp_raw)
        base = _prepare_repo(tmp, discipline_required, contract_lint_required)
        task_text = (FIXTURE / name).read_text(encoding="utf-8").replace("<base>", base)
        task_path = tmp / "fixtures" / name
        _write(task_path, task_text)
        _write(tmp / "fixtures" / "validate.json", (FIXTURE / "validate.json").read_text(encoding="utf-8"))
        _write(tmp / "fixtures" / "apply.json", (FIXTURE / "apply.json").read_text(encoding="utf-8"))
        _git(tmp, "add", "fixtures")
        _git(tmp, "commit", "-qm", "fixture change")
        completed = subprocess.run(
            [
                sys.executable,
                str(TOOLS / "delivery_check.py"),
                "--root",
                str(tmp),
                "--change",
                "fixture-native",
                "--tasks",
                str(task_path),
                "--validate-json",
                str(tmp / "fixtures" / "validate.json"),
                "--apply-json",
                str(tmp / "fixtures" / "apply.json"),
            ],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        ok = completed.returncode == 0
        if ok != expect_ok:
            print(f"[FAIL] fixture {name}: exit={completed.returncode}, expected_ok={expect_ok}")
            print(completed.stdout)
            print(completed.stderr, file=sys.stderr)
            raise SystemExit(1)
        if expect_message and expect_message not in (completed.stdout + completed.stderr):
            print(f"[FAIL] fixture {name}: 输出缺少预期错误：{expect_message}")
            print(completed.stdout)
            print(completed.stderr, file=sys.stderr)
            raise SystemExit(1)


def main() -> int:
    _run_case("tasks-positive.md", True)
    _run_case("tasks-negative-zero.md", False)
    _run_case("tasks-positive.md", False, discipline_required=True, expect_message="discipline")
    _run_case("tasks-positive.md", False, contract_lint_required=True, expect_message="contract lint")
    print(
        "PASS delivery-check fixtures: positive=0, zero-tasks!=0, "
        "discipline-required-missing!=0, contract-lint-failure!=0 (hermetic repo)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
