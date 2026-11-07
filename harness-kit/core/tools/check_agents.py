#!/usr/bin/env python3
"""通用指令层门禁：AGENTS 存在性/字节上限、token 预算、敏感串、§ 引用解析。

用法：
    python3 tools/check_agents.py [--root PATH]

根目录默认「本脚本上级目录」（脚本位于目标项目 `tools/` 下）；`--root` 可覆盖。
配置唯一来源：`<root>/harness/config.json`。配置缺失 / 必需字段缺失 → 可读报错 exit 1。

检查项：
    a) `config.instructions.root` 存在；`nested` 列表中的文件存在且字节数 ≤ nestedMaxBytes；
    b) `config.instructions.budgets` 中文件 token 数 ≤ 预算；
    c) 敏感串：`config.instructions.sensitivePatterns` + 内置 `/Users/`、设备标识形、
       `sk-` 密钥形，扫描根/嵌套指令文件；
    d) `§N` / `第 N 节` 引用能解析到目标文件且对应编号标题存在：
       同行最近 `.md` 路径 → 「根 AGENTS」→ 根文件自引用；无法定位 → FAIL。

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
FENCE_LINE_RE = re.compile(r"^\s*```")
URL_RE = re.compile(r"https?://\S+")
MD_PATH_RE = re.compile(r"[A-Za-z0-9_.\-/]+\.md")
ROOT_AGENTS_RE = re.compile(r"根\s*AGENTS|根指令|root\s+AGENTS", re.IGNORECASE)
# §5 / §5–§6 / 第 5 节 / 第 5–6 节
SECTION_REF_RE = re.compile(
    r"§\s*(\d+(?:\.\d+)?)(?:\s*[–—~-]\s*§?\s*(\d+(?:\.\d+)?))?"
    r"|第\s*(\d+(?:\.\d+)?)(?:\s*[–—~-]\s*(\d+(?:\.\d+)?))?\s*节"
)
# 内置敏感串：机器绝对路径、设备标识（十六进制连字符）、疑似 API Key。
BUILTIN_SENSITIVE: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("绝对路径 /Users/", re.compile(r"/Users/")),
    (
        "设备标识（十六进制连字符）",
        re.compile(
            r"\b[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\b"
            r"|\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{8,16}\b"
            r"|\b[0-9A-Fa-f]{40}\b"
        ),
    ),
    ("疑似密钥 sk-", re.compile(r"(?:^|[^A-Za-z0-9_])sk-[A-Za-z0-9_\-]{8,}")),
)
BUILTIN_LITERALS = {"/Users/", "sk-"}


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


def relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"config.{label} 缺失或不是非空字符串")
    cleaned = value.strip().replace("\\", "/")
    candidate = Path(cleaned)
    if candidate.is_absolute():
        raise ConfigError(f"config.{label} 必须是相对路径：{value!r}")
    if ".." in candidate.parts:
        raise ConfigError(f"config.{label} 不允许包含 '..'：{value!r}")
    return cleaned


def get_instructions(config: dict) -> dict:
    instructions = config.get("instructions")
    if not isinstance(instructions, dict):
        raise ConfigError("缺少 config.instructions 对象（指令层门禁必需）")
    root_rel = relative_path(instructions.get("root"), "instructions.root")
    nested = instructions.get("nested", [])
    if not isinstance(nested, list) or not all(isinstance(item, str) for item in nested):
        raise ConfigError("config.instructions.nested 必须是字符串数组")
    nested_paths = [relative_path(item, "instructions.nested[]") for item in nested]
    nested_max = instructions.get("nestedMaxBytes")
    if not isinstance(nested_max, int) or nested_max <= 0:
        raise ConfigError("config.instructions.nestedMaxBytes 缺失或不是正整数")
    budgets = instructions.get("budgets", {})
    if budgets is None:
        budgets = {}
    if not isinstance(budgets, dict):
        raise ConfigError("config.instructions.budgets 必须是对象")
    for rel, budget in budgets.items():
        if not isinstance(rel, str) or not rel.strip():
            raise ConfigError("config.instructions.budgets 的键必须是非空文件路径")
        if not isinstance(budget, int) or budget <= 0:
            raise ConfigError(f"config.instructions.budgets[{rel!r}] 必须是正整数")
    patterns = instructions.get("sensitivePatterns", [])
    if patterns is None:
        patterns = []
    if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
        raise ConfigError("config.instructions.sensitivePatterns 必须是字符串数组")
    return {
        "root": root_rel,
        "nested": nested_paths,
        "nestedMaxBytes": nested_max,
        "budgets": budgets,
        "sensitivePatterns": patterns,
    }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def display(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:  # pragma: no cover - 防御性
        return path.as_posix()


def check_instruction_files(root: Path, instructions: dict) -> tuple[list[Path], list[str], list[str]]:
    """返回 (存在的指令文件, 问题, OK 消息)。"""
    problems: list[str] = []
    files: list[Path] = []
    root_file = root / instructions["root"]
    if not root_file.is_file():
        problems.append(f"根指令文件不存在：{instructions['root']}")
    else:
        files.append(root_file)
    for rel in instructions["nested"]:
        path = root / rel
        if not path.is_file():
            problems.append(f"嵌套指令文件不存在：{rel}")
            continue
        files.append(path)
        size = path.stat().st_size
        limit = instructions["nestedMaxBytes"]
        if size > limit:
            problems.append(f"嵌套指令文件超长：{rel} {size} > {limit} bytes")
    messages = [f"指令文件：{len(files)} 个存在（nestedMaxBytes={instructions['nestedMaxBytes']}）"]
    return files, problems, messages


def token_check(root: Path, budgets: dict) -> tuple[list[str], list[str]]:
    if not budgets:
        return [], ["token 预算：config.instructions.budgets 未配置（跳过）"]
    problems: list[str] = []
    for rel, budget in sorted(budgets.items()):
        path = root / rel
        if not path.is_file():
            problems.append(f"token 预算登记的文件不存在：{rel}")
            continue
        tokens = estimate_tokens(read_text(path))
        if tokens > budget:
            problems.append(f"token 超预算：{rel} ≈{tokens} > {budget}")
    return problems, [f"token 预算：{len(budgets)} 个文件均在预算内"]


def sensitive_hits(text: str, configured: list[str]) -> list[tuple[int, str]]:
    """返回 [(行号, 类别)]；命中内容不回显（避免把密钥打印到日志）。"""
    hits: list[tuple[int, str]] = []
    for label, pattern in BUILTIN_SENSITIVE:
        for match in pattern.finditer(text):
            hits.append((text.count("\n", 0, match.start()) + 1, label))
    for pattern in configured:
        if pattern in BUILTIN_LITERALS:
            continue  # 已由内置规则覆盖（避免重复/过宽匹配）
        if not pattern:
            continue
        for match in re.finditer(re.escape(pattern), text):
            hits.append((text.count("\n", 0, match.start()) + 1, f"配置敏感串 {pattern}"))
    return sorted(set(hits))


def check_sensitive(root: Path, files: list[Path], configured: list[str]) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    for path in files:
        text = read_text(path)
        for line, label in sensitive_hits(text, configured):
            problems.append(f"{display(root, path)}:{line}: 敏感串（{label}）")
    return problems, [f"敏感串：扫描 {len(files)} 个指令文件，0 命中"]


def has_heading(text: str, number: str) -> bool:
    pattern = re.compile(
        rf"^#{{1,6}}\s*(?:第\s*)?{re.escape(number)}(?:[.．、:：]|\s|节|$)", re.MULTILINE
    )
    return pattern.search(text) is not None


def resolve_md_path(root: Path, token: str, current_rel: str, dirs: list[str]) -> Path:
    """解析同行 `.md` 路径：项目根 → 当前文件目录 → 常见文档目录兜底。"""
    token = token.replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    candidates: list[Path] = []
    if token.startswith("../"):
        candidates.append((root / current_rel).parent / token)
    candidates.append(root / token)
    if "/" not in token:
        candidates += [root / directory / token for directory in dirs]
        candidates.append((root / current_rel).parent / token)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def resolve_ref_target(
    line: str,
    ref_start: int,
    root: Path,
    current_rel: str,
    instructions: dict,
    dirs: list[str],
) -> Path | None:
    """按 SPEC 规则定位 § 引用的目标文件：同行 .md → 根 AGENTS → 根文件自引用。"""
    prefix = line[:ref_start]
    paths = list(MD_PATH_RE.finditer(prefix))
    if paths:
        return resolve_md_path(root, paths[-1].group(0), current_rel, dirs)
    if ROOT_AGENTS_RE.search(prefix):
        return root / instructions["root"]
    if current_rel == instructions["root"]:
        return root / instructions["root"]
    return None


def check_section_refs(
    root: Path,
    files: list[Path],
    instructions: dict,
    dirs: list[str],
) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    checked = 0
    for path in files:
        current_rel = display(root, path)
        in_fence = False
        for lineno, raw in enumerate(read_text(path).splitlines(), 1):
            if FENCE_LINE_RE.match(raw):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            line = URL_RE.sub(" ", raw)
            for match in SECTION_REF_RE.finditer(line):
                numbers = [group for group in match.groups() if group]
                if not numbers:
                    continue
                target = resolve_ref_target(
                    line, match.start(), root, current_rel, instructions, dirs
                )
                ref_text = "、".join(f"§{number}" for number in numbers)
                if target is None:
                    problems.append(f"{current_rel}:{lineno}: {ref_text} 引用无法定位目标文件")
                    continue
                if not target.is_file():
                    problems.append(
                        f"{current_rel}:{lineno}: {ref_text} 引用目标文件不存在：{display(root, target)}"
                    )
                    continue
                target_text = read_text(target)
                missing = [number for number in numbers if not has_heading(target_text, number)]
                checked += 1
                if missing:
                    holes = "、".join(f"§{number}" for number in missing)
                    problems.append(
                        f"{current_rel}:{lineno}: {display(root, target)} 缺少 {holes} 对应编号标题"
                    )
    messages = [f"§ 引用：{checked} 处命中文件 + 编号标题"] if checked else []
    return problems, messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="通用指令层门禁（AGENTS/预算/敏感串/§ 引用）")
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
        instructions = get_instructions(config)
    except ConfigError as exc:
        print(f"[FAIL] 配置不可用：{exc}")
        return 1

    paths = config.get("paths", {})
    dirs = [
        str(paths.get("docs", "docs")),
        str(paths.get("references", "references")),
        str(paths.get("harness", "harness")),
    ]
    problems: list[str] = []
    files, file_problems, messages = check_instruction_files(root, instructions)
    problems.extend(file_problems)
    for message in messages:
        if not file_problems:
            print(f"[OK] {message}")

    found, messages = token_check(root, instructions["budgets"])
    problems.extend(found)
    for message in messages:
        if not found:
            print(f"[OK] {message}")

    found, messages = check_sensitive(root, files, instructions["sensitivePatterns"])
    problems.extend(found)
    for message in messages:
        if not found:
            print(f"[OK] {message}")

    found, messages = check_section_refs(root, files, instructions, dirs)
    problems.extend(found)
    if not found:
        for message in messages:
            print(f"[OK] {message}")

    if problems:
        for problem in problems:
            print(f"[FAIL] {problem}")
        print(f"[FAIL] check_agents 未通过：{len(problems)} 个问题（exit 1）")
        return 1
    print(f"[OK] check_agents 通过（{len(files)} 个指令文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
