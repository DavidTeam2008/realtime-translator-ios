#!/usr/bin/env python3
"""Agent 适配层：skills 单源同步 / 校验。

单源：`.dsh/skills/*/SKILL.md`（DSH 原生发现；Claude Code 通过 `.claude/skills/` 使用）。
用法：
    python3 tools/adapters.py sync    # 生成/刷新 .claude/skills/（本机生成物，gitignore）
    python3 tools/adapters.py check   # 校验单源、hooks 示例、适配说明；CI/静态门禁用
退出码：0 通过；1 失败。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".dsh" / "skills"
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
ADAPTERS = ROOT / "harness" / "adapters"
CLAUDE_DIR = ADAPTERS / "claude-code"

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def skill_files() -> list[Path]:
    return sorted(SKILLS.glob("*/SKILL.md"))


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    meta: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta


def check() -> int:
    errors: list[str] = []
    skills = skill_files()
    if not skills:
        errors.append(f"缺少 skills：{SKILLS}/<name>/SKILL.md")
    for path in skills:
        meta = frontmatter(path)
        name = meta.get("name", "")
        description = meta.get("description", "")
        if not name:
            errors.append(f"{path.relative_to(ROOT)} 缺 name")
        elif not NAME_RE.match(name):
            errors.append(f"{path.relative_to(ROOT)} name 非 kebab-case：{name}")
        elif name != path.parent.name:
            errors.append(f"{path.relative_to(ROOT)} name 与目录名不一致：{name}")
        if not description:
            errors.append(f"{path.relative_to(ROOT)} 缺 description")

    # 可选：已生成的 .claude/skills 必须与单源一致（未生成则跳过，不强制本机安装 Claude Code）
    if CLAUDE_SKILLS.is_dir():
        generated = {p.parent.name for p in CLAUDE_SKILLS.glob("*/SKILL.md")}
        canonical = {p.parent.name for p in skills}
        missing = canonical - generated
        stale = generated - canonical
        if missing:
            errors.append(f".claude/skills 缺少：{', '.join(sorted(missing))}（运行 make adapters-sync）")
        if stale:
            errors.append(f".claude/skills 有多余：{', '.join(sorted(stale))}（运行 make adapters-sync）")
        for path in skills:
            target = CLAUDE_SKILLS / path.parent.name / "SKILL.md"
            if target.is_file() and target.read_bytes() != path.read_bytes():
                errors.append(f"{target.relative_to(ROOT)} 与单源不一致（运行 make adapters-sync）")

    hooks = CLAUDE_DIR / "settings.hooks.example.json"
    if not hooks.is_file():
        errors.append("缺少 harness/adapters/claude-code/settings.hooks.example.json")
    else:
        try:
            data = json.loads(hooks.read_text(encoding="utf-8"))
            hook_map = data.get("hooks", {})
            if "PostToolUse" not in hook_map or "Stop" not in hook_map:
                errors.append("hooks 示例需包含 PostToolUse 与 Stop")
            commands = json.dumps(data, ensure_ascii=False)
            for expected in ("make check", "make verify-static"):
                if expected not in commands:
                    errors.append(f"hooks 示例缺少命令：{expected}")
        except json.JSONDecodeError as exc:
            errors.append(f"hooks 示例不是合法 JSON：{exc}")

    claude_md = CLAUDE_DIR / "CLAUDE.md.template"
    if not claude_md.is_file():
        errors.append("缺少 harness/adapters/claude-code/CLAUDE.md.template")
    elif "@AGENTS.md" not in claude_md.read_text(encoding="utf-8"):
        errors.append("CLAUDE.md.template 应通过 @AGENTS.md 复用单一规则源")

    reviewer = CLAUDE_DIR / "agents" / "red-team.md"
    if not reviewer.is_file():
        errors.append("缺少 harness/adapters/claude-code/agents/red-team.md")
    else:
        meta = frontmatter(reviewer)
        if not meta.get("name") or not meta.get("description"):
            errors.append("red-team agent 需 name/description frontmatter")

    if errors:
        print("[FAIL] adapters 校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"[PASS] adapters 校验通过（{len(skills)} 个 skills；Claude Code hooks/CLAUDE.md/agent 示例就绪）")
    return 0


def sync() -> int:
    skills = skill_files()
    if not skills:
        print(f"[FAIL] 缺少 skills：{SKILLS}/<name>/SKILL.md")
        return 1
    if CLAUDE_SKILLS.exists():
        shutil.rmtree(CLAUDE_SKILLS)
    CLAUDE_SKILLS.mkdir(parents=True)
    for path in skills:
        dest = CLAUDE_SKILLS / path.parent.name
        shutil.copytree(path.parent, dest)
    print(f"已同步 {len(skills)} 个 skills → {CLAUDE_SKILLS.relative_to(ROOT)}（gitignore 生成物）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent 适配层同步/校验")
    parser.add_argument("action", choices=["sync", "check"])
    args = parser.parse_args()
    return sync() if args.action == "sync" else check()


if __name__ == "__main__":
    sys.exit(main())
