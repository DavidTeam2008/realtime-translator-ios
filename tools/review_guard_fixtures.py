#!/usr/bin/env python3
"""Hermetic fixtures for the review-independence guard."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "tools" / "review_guard.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
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


def _base_files(root: Path, head: str) -> None:
    _write(
        root / "harness" / "config.json",
        json.dumps(
            {
                "delivery": {
                    "review": {
                        "required": True,
                        "mode": "dual-context",
                        "requireGateRunner": True,
                        "requiredGateCommands": ["python3 tools/check-test-baseline.py"],
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    _write(
        root / "openspec" / "changes" / "c1" / "tasks.md",
        f"""# Delivery Contract

- Change: c1
- Level: L2
- Base: {head}
- Review: required; path=harness/reviews/review.md; covers Base..Head; P0/P1 closed

## Tasks

### Task 1: fixture

- [x] Task 1: fixture task.

**Files:** fixtures/
""",
    )
    _write(
        root / "harness" / "reviews" / "review.md",
        f"""---
base: {head}
head: {head}
reviewer: reviewer-a
p0: closed
p1: closed
p2: closed
verdict: pass
review_mode: dual-context
executor: mattpocock-code-review
axes: standards,spec
standards_report: harness/reviews/review-standards.md
spec_report: harness/reviews/review-spec.md
gate_report: harness/reviews/review-gates.md
gate_runner: gate-runner-b
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
        root / "harness" / "reviews" / "review-gates.md",
        """# gate runner

| command | exit | result |
| --- | --- | --- |
| python3 tools/check-test-baseline.py | 0 | PASS |
""",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="review-guard-fixture-") as raw:
        root = Path(raw)
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "fixture@example.invalid")
        _git(root, "config", "user.name", "fixture")
        _write(root / "README.md", "base\n")
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

        review = root / "harness" / "reviews" / "review.md"
        original = review.read_text(encoding="utf-8")
        cases = {
            "single-context": original.replace("review_mode: dual-context", "review_mode: single-context"),
            "missing-spec-report": original.replace(
                "spec_report: harness/reviews/review-spec.md",
                "spec_report: harness/reviews/missing-spec.md",
            ),
            "head-mismatch": original.replace(f"head: {head}", "head: " + "0" * 40),
            "p1-without-fix-review": original.replace(
                "p1: closed",
                "p1: closed\np1_opened: 1",
            ),
        }
        for name, text in cases.items():
            review.write_text(text, encoding="utf-8")
            completed = _run(root)
            if completed.returncode == 0:
                print(f"[FAIL] negative case unexpectedly passed: {name}", file=sys.stderr)
                return 1
        review.write_text(original, encoding="utf-8")

        gates = root / "harness" / "reviews" / "review-gates.md"
        gates.write_text("# gate runner\n\n| command | exit | result |\n| --- | --- | --- |\n| python3 tools/check-test-baseline.py | 0 | FAIL |\n", encoding="utf-8")
        if _run(root).returncode == 0:
            print("[FAIL] gate without PASS unexpectedly passed", file=sys.stderr)
            return 1
        gates.write_text(
            "# gate runner\n\n| command | exit | result |\n| --- | --- | --- |\n| python3 tools/check-test-baseline.py | 0 | PASS |\n",
            encoding="utf-8",
        )

        print("PASS review-guard fixtures: dual-context positive + 5 negative cases")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
