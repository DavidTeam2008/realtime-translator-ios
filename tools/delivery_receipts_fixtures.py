#!/usr/bin/env python3
"""Hermetic smoke fixtures for host receipt generation + provenance gate."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "tools" / "vendor"
GENERATOR = ROOT / "tools" / "delivery_receipts.py"
STUB = '''#!/usr/bin/env python3
import json
import sys
from pathlib import Path
root = Path.cwd()
args = sys.argv[1:]
if args[:2] == ["new", "change"]:
    change = args[2]
    directory = root / "openspec" / "changes" / change
    directory.mkdir(parents=True, exist_ok=True)
    (directory / ".openspec.yaml").write_text("schema: spec-driven\\ncreated: 2026-11-19\\n", encoding="utf-8")
    print("created")
elif args[0] == "instructions":
    print(json.dumps({"artifact": args[1]}))
elif args[0] == "validate":
    print(json.dumps({"items": [{"id": args[1], "valid": True}]}))
else:
    print("unsupported", file=sys.stderr)
    sys.exit(2)
'''


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def env() -> dict[str, str]:
    value = dict(os.environ)
    value["PYTHONPATH"] = str(VENDOR)
    return value


def provenance_verify(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_delivery_toolchain.provenance_cli",
            "verify",
            "--root",
            str(root),
            "--change",
            "c1",
            "--receipts-dir",
            "harness/receipts/openspec",
        ],
        cwd=root,
        env=env(),
        capture_output=True,
        text=True,
    )


def lint(root: Path, stage: str) -> tuple[subprocess.CompletedProcess[str], dict | None]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_delivery_toolchain.lint_cli",
            "change",
            "--root",
            str(root),
            "--change",
            "c1",
            "--stage",
            stage,
        ],
        cwd=root,
        env=env(),
        capture_output=True,
        text=True,
    )
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError:
        document = None
    return completed, document if isinstance(document, dict) else None


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def issues(document: dict | None, rule: str) -> list[dict]:
    if not document:
        return []
    return [item for item in document.get("issues", []) if item.get("rule") == rule]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="receipt-fixture-") as raw:
        root = Path(raw)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "fixture"], cwd=root, check=True)
        (root / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
        stub = root / "stub-openspec"
        stub.write_text(STUB, encoding="utf-8")
        stub.chmod(0o755)
        for command in (
            [sys.executable, str(GENERATOR), "scaffold", "--root", str(root), "--change", "c1", "--openspec", str(stub)],
            [sys.executable, str(GENERATOR), "instructions", "--root", str(root), "--change", "c1", "--artifact", "proposal", "--openspec", str(stub)],
        ):
            completed = run(command, root)
            if completed.returncode != 0:
                print(completed.stdout)
                print(completed.stderr, file=sys.stderr)
                return 1
        change_dir = root / "openspec" / "changes" / "c1"
        for rel, text in {
            "proposal.md": "# Proposal\n",
            "design.md": "# Design\n",
            "specs/core/spec.md": "# Spec\n",
            "tasks.md": "# Delivery Contract\n",
        }.items():
            path = change_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        for artifact in ("design", "specs", "tasks"):
            completed = run(
                [sys.executable, str(GENERATOR), "instructions", "--root", str(root), "--change", "c1", "--artifact", artifact, "--openspec", str(stub)],
                root,
            )
            if completed.returncode != 0:
                print(completed.stderr, file=sys.stderr)
                return 1
        validate = run(
            [sys.executable, str(GENERATOR), "validate", "--root", str(root), "--change", "c1", "--openspec", str(stub)],
            root,
        )
        if validate.returncode != 0:
            print(validate.stdout)
            print(validate.stderr, file=sys.stderr)
            return 1
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "receipts"], cwd=root, check=True)

        verify = provenance_verify(root)
        if verify.returncode != 0:
            print(verify.stdout)
            print(verify.stderr, file=sys.stderr)
            return 1

        notes = root / "clarification-notes.md"
        notes.write_text("Q: fixture ambiguity?\nA: none.\n", encoding="utf-8")
        clarified = run(
            [
                sys.executable,
                str(GENERATOR),
                "clarification",
                "--root",
                str(root),
                "--change",
                "c1",
                "--skill",
                "brainstorming",
                "--notes",
                str(notes),
            ],
            root,
        )
        if clarified.returncode != 0:
            print(clarified.stdout)
            print(clarified.stderr, file=sys.stderr)
            return 1
        clarification = json.loads(
            (root / "harness" / "receipts" / "clarification" / "c1" / "clarification.json").read_text(encoding="utf-8")
        )
        if clarification.get("kind") != "clarification" or clarification.get("notesSha256") != sha_file(notes):
            print("[FAIL] clarification receipt 未绑定 notes 哈希", file=sys.stderr)
            return 1

        proposal = change_dir / "proposal.md"
        original = proposal.read_text(encoding="utf-8")
        proposal.write_text(original + "\nchanged after validate\n", encoding="utf-8")
        stale = provenance_verify(root)
        if stale.returncode == 0:
            print("[FAIL] validate 后改工件未被 provenance gate 拦截", file=sys.stderr)
            return 1
        proposal.write_text(original, encoding="utf-8")

        for name in ("validate-receipt.json", "scaffold.json"):
            receipt = root / "harness" / "receipts" / "openspec" / "c1" / name
            backup = receipt.read_bytes()
            receipt.unlink()
            missing = provenance_verify(root)
            if missing.returncode == 0:
                print(f"[FAIL] 缺 {name} 未被 provenance gate 拦截", file=sys.stderr)
                return 1
            receipt.write_bytes(backup)

        _, document = lint(root, "plan")
        if not issues(document, "L11"):
            print("[FAIL] 无澄清记录时应产生 L11 WARN", file=sys.stderr)
            return 1
        proposal.write_text(original + "\n无需澄清：fixture 无歧义。\n", encoding="utf-8")
        _, document = lint(root, "plan")
        if issues(document, "L11"):
            print("[FAIL] 存在无需澄清理由时不应产生 L11", file=sys.stderr)
            return 1
        proposal.write_text(original, encoding="utf-8")

        plans = root / "docs" / "superpowers" / "plans"
        plans.mkdir(parents=True)
        (plans / "plan.md").write_text("# second plan\n", encoding="utf-8")
        _, document = lint(root, "delivery")
        if not [item for item in issues(document, "L10") if item.get("level") == "ERROR"]:
            print("[FAIL] docs/superpowers/plans 未被 L10 拦截", file=sys.stderr)
            return 1
        shutil.rmtree(root / "docs")

        print("PASS receipt fixtures: provenance positive + stale/missing negatives + clarification L11 + L10")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
