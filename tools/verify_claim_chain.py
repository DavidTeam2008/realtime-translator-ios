#!/usr/bin/env python3
"""Run the kit evidence verdict, then enforce the host manifest chain for new claims."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import evidence_chain

KIT_VERIFY = Path("tools") / "verify_claim.py"


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    if "--root" in argv:
        index = argv.index("--root")
        if index + 1 >= len(argv):
            print("[FAIL] --root 需要一个目录参数", file=sys.stderr)
            return 2
        root = Path(argv[index + 1]).expanduser().resolve()
    kit = root / KIT_VERIFY
    if not kit.is_file():
        print(f"[FAIL] 缺 {kit}", file=sys.stderr)
        return 2
    completed = subprocess.run(
        [sys.executable, str(kit), *argv],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        return completed.returncode
    try:
        errors = evidence_chain.check_evidence(root)
    except evidence_chain.EvidenceChainError as exc:
        print(f"[FAIL] 证据链校验失败：{exc}")
        return 1
    if errors:
        for item in errors:
            print(item)
        print(f"结论：FAIL（证据链 {len(errors)} 项未通过）")
        return 1
    print("证据链：PASS（pin、manifest、严格 JUnit 重算）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
