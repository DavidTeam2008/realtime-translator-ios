#!/usr/bin/env python3
"""Hermetic fixtures for Superpowers skill receipts + overlay binding."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
VENDOR = TOOLS / "vendor"
GENERATOR = TOOLS / "delivery_receipts.py"

sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(VENDOR))

from ai_delivery_toolchain.delivery import (  # noqa: E402
    DeliveryError,
    _check_optional_modules,
    parse_contract,
    parse_tasks,
)
from ai_delivery_toolchain.skills import SkillError, load_manifest, verify_skill_receipt  # noqa: E402
from delivery_check import check_skill_overlays  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="skills-fixture-") as raw:
        root = Path(raw)
        git(root, "init", "-q")
        git(root, "config", "user.email", "fixture@example.invalid")
        git(root, "config", "user.name", "fixture")
        write(root / "README.md", "base\n")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "base")
        head = git(root, "rev-parse", "HEAD")

        overlay = root / "harness" / "superpowers-overlay.md"
        overlay.parent.mkdir(parents=True, exist_ok=True)
        overlay.write_bytes((ROOT / "harness" / "superpowers-overlay.md").read_bytes())

        host_root = root / "hostskills"
        skill_rel = "skills/test-driven-development/SKILL.md"
        skill_file = host_root / skill_rel
        write(skill_file, "# fixture TDD discipline\n")
        manifest_path = root / "fixture-skills.manifest.json"
        write(
            manifest_path,
            json.dumps(
                {
                    "schemaVersion": 1,
                    "sources": {
                        "superpowers-fixture": {
                            "version": "v7.0.2-fixture",
                            "commit": "a" * 40,
                            "files": {skill_rel: sha(skill_file)},
                        }
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )

        change_dir = root / "openspec" / "changes" / "c1"
        write(
            change_dir / "tasks.md",
            f"""# Delivery Contract

- Change: c1
- Level: L2
- Owner: fixture
- Base: {head}
- Scope allow: openspec/changes/c1/
- Scope deny: Duiyi/
- Acceptance: A1=fixture behavior (unit-tests-pass)
- Verify: make check
- Evidence: unit-tests-pass (required)
- Review: not required
- Archive gate: all tasks checked
- CI: not applicable

## Tasks

### Task 1: red test

- [ ] Task 1: failing test exists before implementation.

**Files:** tests/a.swift

1. Add failing fixture test.
   - Expected: test fails.
   - Covers: A1

### Task 2: green implementation

- [ ] Task 2: implementation makes the fixture test pass.

**Files:** src/a.swift

1. Implement fixture behavior.
   - Expected: test passes.
   - Covers: A1
""",
        )

        generated = run(
            [
                sys.executable,
                str(GENERATOR),
                "skill-receipt",
                "--root",
                str(root),
                "--change",
                "c1",
                "--task",
                "1",
                "--phase",
                "tdd",
                "--skill",
                "test-driven-development",
                "--root-id",
                "fixture",
                "--host-root",
                str(host_root),
                "--host-file",
                str(skill_file),
                "--manifest",
                str(manifest_path),
            ]
        )
        if generated.returncode != 0:
            print(generated.stdout)
            print(generated.stderr, file=sys.stderr)
            return 1
        receipt_path = root / "harness" / "receipts" / "skills" / "c1" / "task-1-test-driven-development.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("overlay", {}).get("sha256") != sha(overlay):
            print("[FAIL] skill receipt 未绑定 overlay 哈希", file=sys.stderr)
            return 1

        git(root, "add", "-A")
        git(root, "commit", "-qm", "receipts")

        manifest = load_manifest(manifest_path)
        verify_skill_receipt(
            root,
            receipt_path,
            manifest,
            expected_change="c1",
            expected_task=1,
            roots={"fixture": host_root},
        )
        check_skill_overlays(root, "c1")

        original_skill = skill_file.read_bytes()
        skill_file.write_bytes(original_skill + b"tampered\n")
        try:
            verify_skill_receipt(
                root,
                receipt_path,
                manifest,
                expected_change="c1",
                expected_task=1,
                roots={"fixture": host_root},
            )
        except SkillError:
            pass
        else:
            print("[FAIL] host skill 哈希被改后未被拦截", file=sys.stderr)
            return 1
        skill_file.write_bytes(original_skill)

        try:
            verify_skill_receipt(
                root,
                receipt_path,
                manifest,
                expected_change="c1",
                expected_task=2,
                roots={"fixture": host_root},
            )
        except SkillError:
            pass
        else:
            print("[FAIL] 错 task 的 skill receipt 未被拦截", file=sys.stderr)
            return 1

        original_receipt = receipt_path.read_bytes()
        receipt["overlay"]["sha256"] = "0" * 64
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            check_skill_overlays(root, "c1")
        except ValueError:
            pass
        else:
            print("[FAIL] overlay 哈希失效未被宿主拦截", file=sys.stderr)
            return 1
        receipt_path.write_bytes(original_receipt)

        tasks_text = (change_dir / "tasks.md").read_text(encoding="utf-8")
        contract = parse_contract(tasks_text)
        tasks = parse_tasks(tasks_text)
        profile = {
            "skills": {
                "required": True,
                "manifest": "fixture-skills.manifest.json",
                "roots": {"fixture": str(host_root)},
            }
        }
        try:
            _check_optional_modules(root, contract, profile, tasks, head)
        except DeliveryError as exc:
            if "task 2 缺少 skill receipt" not in str(exc):
                print(f"[FAIL] 缺 task receipt 报错不符合预期：{exc}", file=sys.stderr)
                return 1
        else:
            print("[FAIL] 缺 task 2 skill receipt 未被拦截", file=sys.stderr)
            return 1

        print("PASS skills fixtures: overlay binding + tampered host/wrong task/overlay/missing receipt")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
