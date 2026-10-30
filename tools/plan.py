#!/usr/bin/env python3
"""跨会话计划：新建、取最新、打印交接摘要。

用法：
  python3 tools/plan.py new <topic>
  python3 tools/plan.py latest
  python3 tools/plan.py brief
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANS = ROOT / ".apm" / "plans"
TEMPLATE = PLANS / "_template.md"


def plans() -> list[Path]:
    return sorted(p for p in PLANS.glob("*.md") if p.name != "_template.md")


def latest() -> Path:
    found = plans()
    if not found:
        sys.exit("没有计划文件；先运行：make plan TOPIC=<topic>")
    return max(found, key=lambda p: (p.stat().st_mtime, p.name))


def resolve(arg: str | None) -> Path:
    if not arg:
        return latest()
    path = Path(arg)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        sys.exit(f"计划不存在：{arg}")
    return path


PLACEHOLDERS = {
    "",
    "-",
    "- [ ]",
    "- [x]",
    "1.",
    "1",
    "文件 / 意图 / 是否可丢弃：",
    "方案 / 失败原因 / 证据：",
    "- 目标：",
    "- 验收（可执行判据）：",
}


def section(text: str, title: str) -> str:
    match = re.search(rf"{re.escape(title)}\n(.*?)(?=\n## |\Z)", text, re.S)
    if not match:
        return ""
    lines = [line for line in match.group(1).splitlines() if line.strip() not in PLACEHOLDERS]
    return "\n".join(lines).strip()


def new(topic: str) -> None:
    if not TEMPLATE.is_file():
        sys.exit(f"缺少模板：{TEMPLATE.relative_to(ROOT)}")
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", topic.strip().lower()).strip("-")
    if not slug:
        sys.exit("TOPIC 需包含字母、数字或汉字")
    path = PLANS / f"{dt.date.today().isoformat()}-{slug}.md"
    if path.exists():
        sys.exit(f"已存在：{path.relative_to(ROOT)}")
    PLANS.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"已创建 {path.relative_to(ROOT)}；填完目标与验收后开工。")


def brief(arg: str | None = None) -> None:
    path = resolve(arg)
    text = path.read_text(encoding="utf-8")
    print(f"按 AGENTS.md 接手；先读 {path.relative_to(ROOT)}，再继续。\n")
    for title in (
        "## 进度",
        "## 已排除（勿重试）",
        "## 验证证据",
        "## 未提交改动",
        "## 下一步",
        "## 待确认",
    ):
        body = section(text, title)
        if body:
            print(f"{title}\n{body}\n")
    for required in ("## 目标与验收", "## 下一步"):
        if not section(text, required):
            print(f"[WARN] 计划缺少{required.lstrip('# ')}，交接前补齐。\n")
    changed = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, text=True, capture_output=True
    ).stdout.strip()
    print("git status --short:")
    print(changed or "(clean)")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "new":
        if len(argv) < 2:
            sys.exit("用法：plan.py new <topic>")
        new(" ".join(argv[1:]))
        return 0
    if cmd == "latest":
        print(latest().relative_to(ROOT))
        return 0
    if cmd == "brief":
        brief(argv[1] if len(argv) > 1 else None)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
