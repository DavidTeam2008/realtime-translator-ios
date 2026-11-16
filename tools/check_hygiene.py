#!/usr/bin/env python3
"""通用宿主卫生检查（配置驱动；标准库；不联网）。

用法：
    python3 tools/check_hygiene.py [--root PATH] [--verbose]

根目录默认「本脚本上级目录」；`--root` 可覆盖。配置唯一来源是
`<root>/harness/config.json` 的 `hygiene` 段（**可选**）：

    "hygiene": {
      "trackedArtifactGlobs": ["**/build/**", "*.log"],
      "rootAllowlist": ["README.md", "AGENTS.md"],
      "localPathPatterns": ["<绝对路径前缀，以 / 开头并以 / 结尾>"],
      "skipLocalPathScan": ["docs/_archive/"],
      "maxTrackedFileBytes": 5242880,
      "forbidAbsoluteSymlinks": true
    }

- `hygiene` 缺失 → `[SKIP]`，exit 0（新接入项目默认通过）。
- 目录型本机路径模式（以 `/` 开头且以 `/` 结尾的绝对路径前缀，例如用户主目录、
  外接磁盘、Unix home）用「前面不是标识符字符」的边界匹配，避免把相对目录
  `features/home/` 误判成本机路径；其余模式按正则处理。
- 检查项：被跟踪的构建产物、根目录文件白名单、绝对符号链接、跟踪文本文件里
  的本机路径、超过 `maxTrackedFileBytes` 的跟踪文件。
- 非 git 仓库 → `[SKIP]`，exit 0（没有「跟踪文件」可查）。
- 本机路径扫描输出覆盖范围：`扫描 S / 跳过 K（pattern=count…）`；`--verbose`
  额外列出最多 20 个被跳过的路径（skipLocalPathScan 的覆盖范围必须可见）。
- 有违规 → 逐条 `[FAIL]`，exit 1。

不写文件、不联网、无第三方依赖。
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

CONFIG_REL = Path("harness") / "config.json"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
# 视为「可扫描文本」的常见后缀；二进制/大文件由 maxTrackedFileBytes 兜底。
TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".rst", ".kt", ".kts", ".java", ".swift",
    ".py", ".js", ".mjs", ".ts", ".sh", ".bash", ".zsh", ".yml", ".yaml",
    ".json", ".xml", ".toml", ".ini", ".cfg", ".properties", ".gradle",
    ".c", ".h", ".cpp", ".hpp", ".cmake", ".gitignore", ".gitattributes",
}


class ConfigError(Exception):
    """配置缺失 / 类型非法（可读报错 → exit 1）。"""


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def load_hygiene(root: Path) -> dict | None:
    """返回 hygiene 配置；缺失章节返回 None。"""
    path = root / CONFIG_REL
    if not path.is_file():
        raise ConfigError(f"缺少配置文件 {CONFIG_REL.as_posix()}（相对 {root}）")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{CONFIG_REL.as_posix()} 不是合法 JSON：{exc}") from exc
    if not isinstance(config, dict):
        raise ConfigError(f"{CONFIG_REL.as_posix()} 顶层必须是 JSON 对象")
    hygiene = config.get("hygiene")
    if hygiene is None:
        return None
    if not isinstance(hygiene, dict):
        raise ConfigError("config.hygiene 必须是对象")
    return hygiene


def list_field(hygiene: dict, key: str) -> list[str]:
    value = hygiene.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ConfigError(f"config.hygiene.{key} 必须是非空字符串数组")
    return list(value)


def int_field(hygiene: dict, key: str, default: int) -> int:
    value = hygiene.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"config.hygiene.{key} 必须是正整数")
    return value


def bool_field(hygiene: dict, key: str, default: bool) -> bool:
    value = hygiene.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"config.hygiene.{key} 必须是布尔值")
    return value


def compile_local_patterns(patterns: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for pattern in patterns:
        if pattern.startswith("/") and pattern.endswith("/"):
            # 目录型绝对路径：前面不是标识符字符，避免把相对目录 features/home/ 误判。
            compiled.append(
                (pattern, re.compile(r"(?<![A-Za-z0-9_.\-])" + re.escape(pattern)))
            )
        else:
            try:
                compiled.append((pattern, re.compile(pattern)))
            except re.error as exc:
                raise ConfigError(f"config.hygiene.localPathPatterns 非法正则 {pattern!r}：{exc}") from exc
    return compiled


def git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def tracked_files(root: Path) -> list[str] | None:
    output = git(root, "ls-files", "-z")
    if output is None:
        return None
    return [item for item in output.split("\0") if item]


def tracked_symlinks(root: Path) -> list[tuple[str, str]]:
    """返回 mode=120000 的跟踪符号链接 [(路径, 目标)]。"""
    output = git(root, "ls-files", "-s", "-z")
    if output is None:
        return []
    links: list[tuple[str, str]] = []
    for entry in [item for item in output.split("\0") if item]:
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        if len(parts) < 3 or parts[0] != "120000":
            continue
        target = git(root, "cat-file", "-p", parts[1])
        if target is not None:
            links.append((path, target.strip()))
    return links


def check_hygiene(root: Path, hygiene: dict) -> dict:
    problems: list[str] = []
    artifact_globs = list_field(hygiene, "trackedArtifactGlobs")
    root_allowlist = set(list_field(hygiene, "rootAllowlist"))
    skip_scan = tuple(list_field(hygiene, "skipLocalPathScan"))
    max_bytes = int_field(hygiene, "maxTrackedFileBytes", DEFAULT_MAX_BYTES)
    forbid_symlinks = bool_field(hygiene, "forbidAbsoluteSymlinks", True)
    local_patterns = compile_local_patterns(list_field(hygiene, "localPathPatterns"))

    files = tracked_files(root) or []
    stats = {
        "tracked": len(files),
        "localScanned": 0,
        "skippedLocal": 0,
        "skipPatterns": {},
        "skippedPaths": [],
        "localPathScanEnabled": bool(local_patterns),
    }

    # 1) 被跟踪的构建产物
    for relative in files:
        basename = Path(relative).name
        for pattern in artifact_globs:
            if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(basename, pattern):
                problems.append(f"被跟踪的构建产物：{relative}（命中 {pattern}）")
                break

    # 2) 根目录文件白名单（仅当配置了白名单时生效）
    if root_allowlist:
        for relative in files:
            if "/" not in relative and relative not in root_allowlist:
                problems.append(f"根目录文件不在 hygiene.rootAllowlist：{relative}")

    # 3) 绝对符号链接
    if forbid_symlinks:
        for relative, target in tracked_symlinks(root):
            if target.startswith("/"):
                problems.append(f"绝对符号链接：{relative} -> {target}")

    # 4) 跟踪文本文件里的本机路径（同时统计 skipLocalPathScan 的覆盖范围）
    if local_patterns:
        for relative in files:
            matched_skips = [prefix for prefix in skip_scan if relative.startswith(prefix)]
            if matched_skips:
                stats["skippedLocal"] += 1
                stats["skippedPaths"].append(relative)
                for prefix in matched_skips:
                    stats["skipPatterns"][prefix] = stats["skipPatterns"].get(prefix, 0) + 1
                continue
            suffix = Path(relative).suffix or Path(relative).name
            if suffix not in TEXT_SUFFIXES:
                continue
            path = root / relative
            if not path.is_file() or path.is_symlink():
                continue
            try:
                if path.stat().st_size > max_bytes:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            stats["localScanned"] += 1
            for pattern_text, pattern in local_patterns:
                match = pattern.search(text)
                if match:
                    problems.append(f"本机路径入库：{relative}（命中模式 {pattern_text}）")
                    break

    # 5) 超大跟踪文件
    for relative in files:
        path = root / relative
        if path.is_file() and not path.is_symlink() and path.stat().st_size > max_bytes:
            problems.append(f"跟踪文件超过 {max_bytes} bytes：{relative}")

    stats["problems"] = problems
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="通用宿主卫生检查（跟踪产物/本机路径/符号链接）")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="项目根（默认脚本上级目录）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="列出被 skipLocalPathScan 跳过的路径（最多 20 个）",
    )
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        fail(f"根目录不存在：{root}")
        return 1

    try:
        hygiene = load_hygiene(root)
    except ConfigError as exc:
        fail(f"配置不可用：{exc}")
        return 1

    if hygiene is None:
        print("[SKIP] 未配置 hygiene（harness/config.json），跳过宿主卫生检查")
        return 0
    if tracked_files(root) is None:
        print("[SKIP] 不是 git 仓库，跳过宿主卫生检查")
        return 0

    try:
        stats = check_hygiene(root, hygiene)
    except ConfigError as exc:
        fail(f"配置不可用：{exc}")
        return 1

    problems = stats["problems"]
    if stats["localPathScanEnabled"]:
        pattern_counts = "、".join(
            f"{pattern}={count}"
            for pattern, count in sorted(stats["skipPatterns"].items())
        ) or "无"
        print(
            f"[OK] 本机路径扫描：扫描 {stats['localScanned']} 个跟踪文件 / "
            f"跳过 {stats['skippedLocal']}（{pattern_counts}）"
        )
        if args.verbose and stats["skippedPaths"]:
            for skipped in stats["skippedPaths"][:20]:
                print(f"[SKIP] {skipped}")
            hidden = len(stats["skippedPaths"]) - 20
            if hidden > 0:
                print(f"[SKIP] …（还有 {hidden} 个被跳过的路径）")

    if problems:
        for problem in problems:
            fail(problem)
        print(f"[FAIL] check_hygiene 发现 {len(problems)} 个卫生问题（exit 1）")
        return 1
    print(f"[OK] 卫生检查：{stats['tracked']} 个跟踪文件，0 违规")
    return 0


if __name__ == "__main__":
    sys.exit(main())
