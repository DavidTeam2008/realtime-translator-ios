#!/usr/bin/env python3
"""文档自检：相对链接、代码围栏、docs 索引覆盖、公开文档白名单、token 预算。

只扫当前事实源：根 README/AGENTS/HARNESS/CONTRIBUTING、docs/*.md、references/*.md、
.apm/**/*.md；跳过 .apm/runs/ 与 _archive/。公开文档白名单与数量上限用于防止
"删了又长回来"：新增/删除公开文档必须显式修改本文件。
token 预算从 tools/rules-budget.json 读取，估算口径见 tools/token_estimate.py；
每次运行都打印每个受控文件的已用/预算/余量。
用法：python3 tools/check-docs.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from token_estimate import estimate_tokens

ROOT = Path(__file__).resolve().parent.parent
ROOT_DOCS = ("README.md", "AGENTS.md", "HARNESS.md", "CONTRIBUTING.md")
# 公开 docs 白名单：第二批历史文档归档后，需同步缩短本集合并把上限降到 9。
PUBLIC_DOCS = frozenset({
    "README.md",
    "AGENTS.md",
    "01-product-design.md",
    "02-architecture.md",
    "03-tech-choices.md",
    "04-roadmap.md",
    "decisions.md",
    "14-device-test-iphone13.md",
    "15-startup-optimization.md",
    "16-startup-measurement-verification.md",
    "17-startup-optimization-paused.md",
    "18-startup-feasibility-verification.md",
    "19-ended-translation-persistence-fix.md",
    "20-ui-test-hittable-fix.md",
    "21-cross-session-handoff.md",
})
PUBLIC_DOCS_BUDGET = 16
ROOT_MD_ALLOWED = frozenset(ROOT_DOCS) | {"AGENTS.local.md", "CLAUDE.local.md"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"^\s*```", re.M)
BUDGET_FILE = ROOT / "tools" / "rules-budget.json"

errors: list[str] = []


def targets() -> list[Path]:
    files = [ROOT / name for name in ROOT_DOCS]
    files += sorted((ROOT / "docs").glob("*.md"))
    files += sorted((ROOT / "references").glob("*.md"))
    for path in sorted((ROOT / ".apm").rglob("*.md")):
        if "runs" in path.parts or "_archive" in path.parts:
            continue
        files.append(path)
    return [p for p in files if p.is_file()]


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def check_links(path: Path) -> int:
    text = strip_code(path.read_text(encoding="utf-8"))
    checked = 0
    for raw in LINK_RE.findall(text):
        target = raw.strip()
        if target.startswith(("http://", "https://", "mailto:", "#", "{{")):
            continue
        local = target.split("#", 1)[0].strip()
        if not local:
            continue
        checked += 1
        if not (path.parent / local).exists():
            errors.append(f"{path.relative_to(ROOT)} 链接不存在：{target}")
    return checked


def check_fences(path: Path) -> None:
    fences = len(FENCE_RE.findall(path.read_text(encoding="utf-8")))
    if fences % 2:
        errors.append(f"{path.relative_to(ROOT)} 代码围栏未闭合（{fences} 个 ```）")


def check_public_docs() -> None:
    docs = sorted((ROOT / "docs").glob("*.md"))
    for path in docs:
        if path.name not in PUBLIC_DOCS:
            errors.append(f"docs/{path.name} 不在公开文档白名单（新增需更新 tools/check-docs.py）")
    if len(docs) > PUBLIC_DOCS_BUDGET:
        errors.append(f"docs/*.md 数量 {len(docs)} 超过上限 {PUBLIC_DOCS_BUDGET}（先归档/蒸馏再新增）")
    root_md = sorted(path.name for path in ROOT.glob("*.md"))
    for name in root_md:
        if name not in ROOT_MD_ALLOWED:
            errors.append(f"根目录 {name} 不在公开入口白名单（只允许 {', '.join(ROOT_DOCS)}）")
    print(f"[OK] 公开文档白名单：docs {len(docs)}/{PUBLIC_DOCS_BUDGET}，根 {len(root_md)} 个 md")


def check_docs_index() -> None:
    index = ROOT / "docs" / "README.md"
    if not index.is_file():
        errors.append("缺少 docs/README.md（文档索引）")
        return
    indexed = {
        (index.parent / raw.split("#", 1)[0]).resolve()
        for raw in LINK_RE.findall(strip_code(index.read_text(encoding="utf-8")))
        if not raw.startswith(("http://", "https://", "#", "{{"))
    }
    for doc in sorted((ROOT / "docs").glob("*.md")):
        if doc.name == "README.md":
            continue
        if doc.resolve() not in indexed:
            errors.append(f"docs/{doc.name} 未登记到 docs/README.md")


def check_budgets() -> None:
    try:
        data = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append("缺少 tools/rules-budget.json（token 预算配置）")
        return
    except json.JSONDecodeError as exc:
        errors.append(f"tools/rules-budget.json 不是合法 JSON：{exc}")
        return
    budgets = data.get("tokenBudgets", {})
    if not budgets:
        errors.append("tools/rules-budget.json 缺少 tokenBudgets")
        return
    print(f"token 口径：{data.get('estimator', 'unknown')}")
    for rel, budget in budgets.items():
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"缺少文件：{rel}")
            continue
        tokens = estimate_tokens(path.read_text(encoding="utf-8"))
        remain = budget - tokens
        status = "OK" if tokens <= budget else "FAIL"
        print(f"[{status}] {rel} ≈ {tokens}/{budget} tokens（余 {remain}）")
        if tokens > budget:
            errors.append(f"{rel} 超出 token 预算：≈{tokens} > {budget}")


def main() -> int:
    files = targets()
    links = sum(check_links(p) for p in files)
    for path in files:
        check_fences(path)
    check_docs_index()
    check_public_docs()

    print(f"扫描 {len(files)} 篇文档，{links} 条相对链接")
    check_budgets()
    if errors:
        print(f"\n[FAIL] {len(errors)} 个问题：")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[PASS] 链接 / 围栏 / docs 索引全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
