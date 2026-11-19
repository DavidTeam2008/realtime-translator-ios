#!/usr/bin/env python3
"""Hermetic fixtures for the review execution-provenance guard."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "tools" / "review_guard.py"
EXECUTOR = "claude-code-code-review-skill"
EXEC_SESSION = "11111111-1111-4111-8111-111111111111"
GATE_SESSION = "22222222-2222-4222-8222-222222222222"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _dump(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise SystemExit(f"fixture git {' '.join(args)} failed: {completed.stderr}")
    return completed.stdout.strip()


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GUARD), "check", "--root", str(root), "--change", "c1"],
        cwd=root,
        capture_output=True,
        text=True,
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _base_files(root: Path, head: str) -> None:
    head7 = head[:7]
    review_rel = "harness/reviews/review.md"
    exec_rel = f"harness/receipts/reviews/c1/{head7}-execution.json"
    events_rel = f"harness/receipts/reviews/c1/{head7}-execution.events.json"
    gate_receipt_rel = f"harness/receipts/reviews/c1/{head7}-gates.json"
    gate_report_rel = "harness/reviews/review-gates.md"

    _dump(
        root / "harness" / "config.json",
        {
            "delivery": {
                "review": {
                    "required": True,
                    "mode": "dual-context",
                    "requireGateRunner": True,
                    "requiredGateCommands": ["python3 tools/check-test-baseline.py"],
                    "executor": {
                        "required": EXECUTOR,
                        "minSubagents": 2,
                        "requiredTools": ["Skill", "Task"],
                        "deniedTools": ["Write", "Edit", "NotebookEdit"],
                    },
                    "receipts": {"required": True, "dir": "harness/receipts/reviews"},
                }
            }
        },
    )
    _write(
        root / "openspec" / "changes" / "c1" / "tasks.md",
        f"""# Delivery Contract

- Change: c1
- Level: L2
- Base: {head}
- Review: required; path={review_rel}; covers Base..Head; P0/P1 closed

## Tasks

### Task 1: fixture

- [x] Task 1: fixture task.

**Files:** fixtures/
""",
    )
    _write(
        root / review_rel,
        f"""---
base: {head}
head: {head}
reviewer: reviewer-a
p0: closed
p1: closed
p2: closed
verdict: pass
review_mode: dual-context
executor: {EXECUTOR}
axes: standards,spec
standards_report: harness/reviews/review-standards.md
spec_report: harness/reviews/review-spec.md
gate_report: {gate_report_rel}
gate_runner: gate-runner-b
execution_receipt: {exec_rel}
gate_receipt: {gate_receipt_rel}
---

# fixture review
""",
    )
    for axis in ("standards", "spec"):
        _write(
            root / "harness" / "reviews" / f"review-{axis}.md",
            f"""---
axis: {axis}
context: isolated
base: {head}
head: {head}
---

# {axis} report
""",
        )
    _write(
        root / gate_report_rel,
        f"""# Gate Run — c1

- Base: {head}
- Head: {head}
- Gate runner: gate-runner-b
- Overall: PASS

| command | exit | result |
| --- | --- | --- |
| python3 tools/check-test-baseline.py | 0 | PASS |

- Receipt: {gate_receipt_rel}
""",
    )
    events_path = root / events_rel
    _dump(
        events_path,
        {
            "schemaVersion": 1,
            "kind": "dual-review-events",
            "entries": [
                {"type": "prompt", "text": f"/code-review {head}"},
                {
                    "type": "subagent_spawn",
                    "tool": "Agent",
                    "description": "Standards axis review",
                    "subagentType": "general-purpose",
                },
                {
                    "type": "subagent_spawn",
                    "tool": "Agent",
                    "description": "Spec axis review",
                    "subagentType": "general-purpose",
                },
                {
                    "type": "subagent",
                    "agentId": "agent-standards",
                    "subagentType": "general-purpose",
                    "taskDescription": "Standards axis review",
                },
                {
                    "type": "subagent",
                    "agentId": "agent-spec",
                    "subagentType": "general-purpose",
                    "taskDescription": "Spec axis review",
                },
                {
                    "type": "result",
                    "sessionId": EXEC_SESSION,
                    "isError": False,
                    "numTurns": 6,
                    "subagentStats": {"spawned": 2},
                },
            ],
        },
    )
    _dump(
        root / exec_rel,
        {
            "schemaVersion": 1,
            "kind": "dual-review-execution",
            "ok": True,
            "change": "c1",
            "base": head,
            "head": head,
            "executor": EXECUTOR,
            "claudeVersion": "2.1.310 (Claude Code)",
            "sessionId": EXEC_SESSION,
            "model": "deepseek-flash",
            "prompt": f"/code-review {head}",
            "command": [
                "claude",
                "-p",
                f"/code-review {head}",
                "--allowedTools",
                "Skill,Task,Agent",
            ],
            "permissions": {
                "allowed": ["Skill", "Task", "Agent", "Read"],
                "disallowed": ["Write", "Edit", "NotebookEdit"],
            },
            "subagentStats": {"spawned": 2},
            "events": {"path": events_rel, "sha256": _sha(events_path)},
            "startedAt": "2026-11-19T00:00:00Z",
            "finishedAt": "2026-11-19T00:05:00Z",
        },
    )
    _dump(
        root / gate_receipt_rel,
        {
            "schemaVersion": 1,
            "kind": "dual-review-gates",
            "change": "c1",
            "base": head,
            "head": head,
            "runner": "gate-runner-b",
            "sessionId": GATE_SESSION,
            "overall": "PASS",
            "commands": [
                {
                    "command": "python3 tools/check-test-baseline.py",
                    "required": True,
                    "exitCode": 0,
                    "durationMs": 1,
                }
            ],
            "requiredGateCommands": ["python3 tools/check-test-baseline.py"],
            "report": {
                "path": gate_report_rel,
                "sha256": _sha(root / gate_report_rel),
            },
            "startedAt": "2026-11-19T00:10:00Z",
            "finishedAt": "2026-11-19T00:10:10Z",
        },
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="review-guard-fixture-") as raw:
        root = Path(raw)
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "fixture@example.invalid")
        _git(root, "config", "user.name", "fixture")
        _write(root / "README.md", "base")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "base")
        head = _git(root, "rev-parse", "HEAD")
        _base_files(root, head)
        # Mirror delivery-check: review artifacts are staged/tracked while HEAD
        # stays at the code commit the review is bound to.
        _git(root, "add", "-A")

        positive = _run(root)
        if positive.returncode != 0:
            print("[FAIL] dual-context positive")
            print(positive.stdout)
            print(positive.stderr, file=sys.stderr)
            return 1

        review_path = root / "harness" / "reviews" / "review.md"
        gate_report = root / "harness" / "reviews" / "review-gates.md"
        exec_path = next((root / "harness" / "receipts" / "reviews" / "c1").glob("*-execution.json"))
        events_path = next(
            (root / "harness" / "receipts" / "reviews" / "c1").glob("*-execution.events.json")
        )
        gate_receipt = next((root / "harness" / "receipts" / "reviews" / "c1").glob("*-gates.json"))
        watched = [review_path, gate_report, exec_path, events_path, gate_receipt]
        originals = {path: path.read_text(encoding="utf-8") for path in watched}

        def restore() -> None:
            for path, text in originals.items():
                path.write_text(text, encoding="utf-8")

        review_text = originals[review_path]
        negative_review_cases = {
            "single-context": ("review_mode: dual-context", "review_mode: single-context"),
            "missing-spec-report": (
                "spec_report: harness/reviews/review-spec.md",
                "spec_report: harness/reviews/missing-spec.md",
            ),
            "head-mismatch": (f"head: {head}", "head: " + "0" * 40),
            "p1-without-fix-review": ("p1: closed", "p1: closed\np1_opened: 1"),
            "executor-not-pinned": (
                f"executor: {EXECUTOR}",
                "executor: custom-single-context",
            ),
            "missing-execution-receipt": (
                f"\nexecution_receipt: harness/receipts/reviews/c1/{head[:7]}-execution.json",
                "",
            ),
            "missing-gate-receipt": (
                f"\ngate_receipt: harness/receipts/reviews/c1/{head[:7]}-gates.json",
                "",
            ),
        }
        for name, (old, new) in negative_review_cases.items():
            if old not in review_text:
                print(f"[FAIL] fixture setup missing mutation anchor: {name}", file=sys.stderr)
                return 1
            review_path.write_text(review_text.replace(old, new, 1), encoding="utf-8")
            completed = _run(root)
            if completed.returncode == 0:
                print(f"[FAIL] negative case unexpectedly passed: {name}", file=sys.stderr)
                return 1
            restore()

        receipt_cases = {
            "missing-task-permission": lambda doc: doc["permissions"]["allowed"].remove("Task"),
            "insufficient-subagents": lambda doc: doc["subagentStats"].update({"spawned": 1}),
            "receipt-head-mismatch": lambda doc: doc.update({"head": "0" * 40}),
        }
        for name, mutate in receipt_cases.items():
            document = _load(exec_path)
            mutate(document)
            _dump(exec_path, document)
            completed = _run(root)
            if completed.returncode == 0:
                print(f"[FAIL] negative case unexpectedly passed: {name}", file=sys.stderr)
                return 1
            restore()

        events_document = _load(events_path)
        events_document["entries"].append({"type": "tool_count", "name": "Write", "count": 1})
        _dump(events_path, events_document)
        if _run(root).returncode == 0:
            print("[FAIL] negative case unexpectedly passed: events-tampered", file=sys.stderr)
            return 1
        restore()

        gate_document = _load(gate_receipt)
        gate_document["commands"][0]["exitCode"] = 1
        _dump(gate_receipt, gate_document)
        if _run(root).returncode == 0:
            print("[FAIL] negative case unexpectedly passed: gate-command-failed", file=sys.stderr)
            return 1
        restore()

        gate_report.write_text(
            originals[gate_report].replace("| 0 | PASS |", "| 0 | FAIL |"),
            encoding="utf-8",
        )
        if _run(root).returncode == 0:
            print("[FAIL] negative case unexpectedly passed: gate-without-PASS", file=sys.stderr)
            return 1
        restore()

        if _run(root).returncode != 0:
            print("[FAIL] restored positive no longer passes", file=sys.stderr)
            return 1

        print("PASS review-guard fixtures: dual-context positive + 13 negative cases")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
