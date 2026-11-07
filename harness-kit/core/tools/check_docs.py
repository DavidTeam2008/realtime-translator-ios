#!/usr/bin/env python3
"""通用文档门禁：相对链接、代码围栏、docs 索引、公开文档收敛、token 预算。

用法：
    python3 tools/check_docs.py [--root PATH]

根目录默认「本脚本上级目录」（脚本位于目标项目 `tools/` 下）；`--root` 可覆盖。
配置唯一来源：`<root>/harness/config.json`（文件位置固定；paths.* 只影响扫描目录）。
配置缺失 / 必需字段缺失 → 打印可读错误并 exit 1，不使用内置默认值。

检查项：
    a) 相对链接存在（跳过 http(s)/mailto/#/{{ 占位）；
    b) 代码围栏成对；
    c) docs 索引：`<docs>/README.md` 存在且 `<docs>/*.md`（除 README）均登记；
    d) 公开文档收敛：根目录 `*.md` 仅允许 `config.docs.rootMarkdownAllowed`；
       `config.docs.publicWhitelist` 是允许集合（缺失条目容忍）；实际 docs/*.md 必须都在集合内且数量 ≤ `publicBudget`；
    e) `config.instructions.budgets` 中文件 token 数 ≤ 预算。

仅标准库；不联网、不写文件。输出以 `[OK]` / `[FAIL]` 开头，失败 exit 1。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:  # 同目录导入（脚本与 token_estimate.py 一起复制到目标项目 tools/）
    from token_estimate import estimate_tokens
except ImportError:  # pragma: no cover - 部署缺文件时给出可读错误
    estimate_tokens = None  # type: ignore[assignment]

CONFIG_REL = Path("harness") / "config.json"
SKIP_DIRS = {"runs", "_archive"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE_COUNT_RE = re.compile(r"^\s*```", re.M)
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "#", "{{", "/")


class ConfigError(Exception):
    """配置缺失 / 类型非法（可读报错 → exit 1）。"""


def load_config(root: Path) -> dict:
    path = root / CONFIG_REL
    if not path.is_file():
        raise ConfigError(f"缺少配置文件 {CONFIG_REL.as_posix()}（相对 {root}）")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{CONFIG_REL.as_posix()} 不是合法 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{CONFIG_REL.as_posix()} 顶层必须是 JSON 对象")
    return data


def relative_path(value: str, label: str) -> str:
    """校验配置里的路径：非空字符串、相对路径、不含上跳。"""
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"config.{label} 缺失或不是非空字符串")
    cleaned = value.strip().replace("\\", "/")
    candidate = Path(cleaned)
    if candidate.is_absolute():
        raise ConfigError(f"config.{label} 必须是相对路径：{value!r}")
    if ".." in candidate.parts:
        raise ConfigError(f"config.{label} 不允许包含 '..'：{value!r}")
    return cleaned


def get_paths(config: dict) -> dict:
    paths = config.get("paths")
    if not isinstance(paths, dict):
        raise ConfigError("缺少 config.paths 对象")
    result = {
        "docs": relative_path(paths.get("docs"), "paths.docs"),
        "references": relative_path(paths.get("references"), "paths.references"),
        "harness": relative_path(paths.get("harness"), "paths.harness"),
    }
    root_docs = paths.get("rootDocs", [])
    if not isinstance(root_docs, list) or not all(isinstance(item, str) for item in root_docs):
        raise ConfigError("config.paths.rootDocs 必须是字符串数组")
    result["rootDocs"] = [relative_path(item, "paths.rootDocs[]") for item in root_docs]
    return result


def get_docs_section(config: dict) -> dict:
    docs = config.get("docs", {})
    if docs is None:
        return {}
    if not isinstance(docs, dict):
        raise ConfigError("config.docs 必须是对象")
    return docs


def get_budgets(config: dict) -> dict:
    instructions = config.get("instructions", {})
    if instructions is None:
        return {}
    if not isinstance(instructions, dict):
        raise ConfigError("config.instructions 必须是对象")
    budgets = instructions.get("budgets", {})
    if budgets is None:
        return {}
    if not isinstance(budgets, dict):
        raise ConfigError("config.instructions.budgets 必须是对象")
    for rel, budget in budgets.items():
        if not isinstance(rel, str) or not rel.strip():
            raise ConfigError("config.instructions.budgets 的键必须是非空文件路径")
        if not isinstance(budget, int) or budget <= 0:
            raise ConfigError(f"config.instructions.budgets[{rel!r}] 必须是正整数")
    return budgets


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def display(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:  # pragma: no cover - 防御性
        return path.as_posix()


def is_skipped(root: Path, path: Path) -> bool:
    try:
        parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:  # pragma: no cover - 防御性
        return False
    return any(part in SKIP_DIRS for part in parts)


def strip_code(text: str) -> str:
    """去掉围栏代码块与行内代码，避免把示例里的链接当真实链接。"""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def collect_files(root: Path, paths: dict) -> tuple[list[Path], list[str]]:
    """返回 (待扫描的 Markdown 文件, 问题列表)。"""
    files: list[Path] = []
    problems: list[str] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            files.append(path)

    for rel in paths["rootDocs"]:
        path = root / rel
        if not path.is_file():
            problems.append(f"config.paths.rootDocs 声明的文件不存在：{rel}")
        else:
            add(path)
    for key in ("docs", "references", "harness"):
        base = root / paths[key]
        if not base.is_dir():
            problems.append(f"目录不存在：{paths[key]}（config.paths.{key}）")
            continue
        for path in sorted(base.rglob("*.md")):
            if path.is_file() and not is_skipped(root, path):
                add(path)
    return files, problems


def check_links(root: Path, files: list[Path]) -> tuple[list[str], str]:
    problems: list[str] = []
    checked = 0
    for path in files:
        text = strip_code(read_text(path))
        for raw in LINK_RE.findall(text):
            target = raw.strip()
            if not target or target.startswith(EXTERNAL_PREFIXES):
                continue
            local = target.split("#", 1)[0].strip()
            if not local:
                continue
            checked += 1
            if not (path.parent / local).exists():
                problems.append(f"{display(root, path)}: 链接不存在：{target}")
    return problems, f"相对链接：{checked} 条全部存在"


def check_fences(root: Path, files: list[Path]) -> tuple[list[str], str]:
    problems: list[str] = []
    for path in files:
        fences = len(FENCE_COUNT_RE.findall(read_text(path)))
        if fences % 2:
            problems.append(f"{display(root, path)}: 代码围栏未闭合（{fences} 个 ```）")
    return problems, f"代码围栏：{len(files)} 篇文档成对"


def check_docs_index(root: Path, paths: dict) -> tuple[list[str], str]:
    docs_dir = root / paths["docs"]
    index = docs_dir / "README.md"
    if not index.is_file():
        return [f"缺少 docs 索引：{paths['docs']}/README.md"], ""
    registered: set[Path] = set()
    for raw in LINK_RE.findall(strip_code(read_text(index))):
        target = raw.strip()
        if not target or target.startswith(EXTERNAL_PREFIXES):
            continue
        local = target.split("#", 1)[0].strip()
        if local:
            registered.add((index.parent / local).resolve())
    problems: list[str] = []
    for page in sorted(docs_dir.glob("*.md")):
        if page.name == "README.md":
            continue
        if page.resolve() not in registered:
            problems.append(f"{display(root, page)} 未登记到 {paths['docs']}/README.md")
    return problems, f"docs 索引：{paths['docs']}/README.md 已登记 {len(registered)} 个目标"


def check_public_docs(root: Path, docs_cfg: dict, docs_rel: str = "docs") -> tuple[list[str], str]:
    """公开文档收敛：根目录 md 白名单 + docs/*.md 必须在 publicWhitelist 内且数量 ≤ publicBudget。"""
    problems: list[str] = []
    notes: list[str] = []
    root_allowed = docs_cfg.get("rootMarkdownAllowed")
    if root_allowed is not None:
        if not isinstance(root_allowed, list) or not all(
            isinstance(item, str) for item in root_allowed
        ):
            problems.append("config.docs.rootMarkdownAllowed 必须是字符串数组")
        else:
            allowed = set()
            for item in root_allowed:
                cleaned = item.replace("\\", "/")
                if cleaned.startswith("./"):
                    cleaned = cleaned[2:]
                allowed.add(cleaned)
            for path in sorted(root.glob("*.md")):
                if path.name not in allowed:
                    problems.append(f"根目录 Markdown 不在 rootMarkdownAllowed：{path.name}")
            notes.append(f"根目录 md 白名单 {len(allowed)} 项")
    whitelist = docs_cfg.get("publicWhitelist")
    if whitelist is not None:
        if not isinstance(whitelist, list) or not all(isinstance(item, str) for item in whitelist):
            problems.append("config.docs.publicWhitelist 必须是字符串数组")
        else:
            allowed = {item.replace("\\", "/").lstrip("./") for item in whitelist}
            docs_dir = root / docs_rel
            published = sorted(docs_dir.glob("*.md")) if docs_dir.is_dir() else []
            for page in published:
                rel = page.relative_to(root).as_posix()
                if rel not in allowed:
                    problems.append(f"公开文档不在 publicWhitelist：{rel}")
            budget = docs_cfg.get("publicBudget")
            if isinstance(budget, int) and budget > 0:
                if len(published) > budget:
                    problems.append(
                        f"公开文档数量 {len(published)} 超过上限 publicBudget={budget}"
                    )
                notes.append(f"公开文档 {len(published)} 篇（上限 {budget}）")
            else:
                notes.append(f"公开文档 {len(published)} 篇（未配置上限）")
    if not notes and not problems:
        notes.append("config.docs 未配置（跳过）")
    return problems, "公开文档：" + "，".join(notes)


def check_budgets(root: Path, budgets: dict) -> tuple[list[str], str]:
    if not budgets:
        return [], "token 预算：config.instructions.budgets 未配置（跳过）"
    problems: list[str] = []
    for rel, budget in sorted(budgets.items()):
        path = root / rel
        if not path.is_file():
            problems.append(f"token 预算登记的文件不存在：{rel}")
            continue
        tokens = estimate_tokens(read_text(path))
        if tokens > budget:
            problems.append(f"token 超预算：{rel} ≈{tokens} > {budget}")
    return problems, f"token 预算：{len(budgets)} 个文件均在预算内"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="通用文档门禁（链接/围栏/索引/公开面/token 预算）")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="目标项目根（默认脚本上级目录）",
    )
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"[FAIL] 根目录不存在：{root}")
        return 1
    if estimate_tokens is None:
        print("[FAIL] 缺少同目录 token_estimate.py（无法估算 token 预算）")
        return 1

    try:
        config = load_config(root)
        paths = get_paths(config)
        docs_cfg = get_docs_section(config)
        budgets = get_budgets(config)
    except ConfigError as exc:
        print(f"[FAIL] 配置不可用：{exc}")
        return 1

    files, problems = collect_files(root, paths)
    checks = (
        lambda: check_links(root, files),
        lambda: check_fences(root, files),
        lambda: check_docs_index(root, paths),
        lambda: check_public_docs(root, docs_cfg, paths["docs"]),
        lambda: check_budgets(root, budgets),
    )
    for check in checks:
        found, message = check()
        problems.extend(found)
        if not found and message:
            print(f"[OK] {message}")

    if problems:
        for problem in problems:
            print(f"[FAIL] {problem}")
        print(f"[FAIL] check_docs 未通过：{len(problems)} 个问题（exit 1）")
        return 1
    print(f"[OK] check_docs 通过（扫描 {len(files)} 篇文档）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
