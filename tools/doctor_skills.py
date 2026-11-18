#!/usr/bin/env python3
"""Read-only check that Claude Code and Qoder share the expected skills."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SKILLS = ("openspec", "superpowers")


def check(root: Path) -> list[str]:
    errors: list[str] = []
    home = Path.home()
    claude = home / ".claude" / "skills"
    agents = home / ".agents" / "skills"
    for name in SKILLS:
        link = claude / name
        source = agents / name
        if not link.is_symlink():
            errors.append(f"{link} 不是用户级软链")
            continue
        try:
            resolved = link.resolve()
        except OSError as exc:
            errors.append(f"{link} 无法解析：{exc}")
            continue
        expected = source.resolve()
        if resolved != expected:
            errors.append(f"{link} 指向 {resolved}，期望 {expected}")
        if not (source / "SKILL.md").is_file():
            errors.append(f"{source}/SKILL.md 不存在")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    errors = check(Path(args.root))
    if errors:
        for error in errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    print("PASS Claude Code skills: " + ", ".join(SKILLS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
