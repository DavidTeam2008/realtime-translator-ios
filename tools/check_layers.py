#!/usr/bin/env python3
"""通用分层守卫（配置驱动；标准库；不联网）。

用法：
    python3 tools/check_layers.py [--root PATH]

根目录默认「本脚本上级目录」；`--root` 可覆盖。配置唯一来源是
`<root>/harness/config.json` 的 `layers` 段（**可选**）：

    "layers": {
      "sourceRoot": "src",
      "extensions": [".kt", ".java", ".py"],
      "exclude": ["vendor/", "legacy/**"],
      "rules": [
        {
          "name": "domain",
          "pathPrefix": "src/domain/",
          "forbiddenImports": ["android.", "androidx.", "features.", "services."],
          "allowedImports": []
        }
      ],
      "symbolGuards": [
        { "name": "engine", "classes": ["Engine"], "allowedPaths": ["src/services/**"] }
      ]
    }

- `layers` 缺失 → `[SKIP]`，exit 0（新接入项目默认通过）。
- 文件发现：git 仓库 = `git ls-files`（tracked）+ `git ls-files --others
  --exclude-standard`（untracked），二者同样按 extensions/sourceRoot/excludes
  过滤；untracked 命中违规同样 FAIL（不能靠未 add 绕过），存在 untracked 源文件时
  输出 WARN「CI 只覆盖 tracked」。非 git 仓库回退文件系统遍历。两种模式都会应用默认排除目录
  （`.git` `.venv` `venv` `node_modules` `build` `dist` `__pycache__`
  `.mypy_cache` `.pytest_cache` `.tox` `.eggs` `*.egg-info` `target`
  `.idea` `.vscode`）与 `layers.exclude`（路径前缀或 glob）。
- `rules`：对 `pathPrefix` 下的源文件，`forbiddenImports` 命中即违规；
  `allowedImports` 可覆盖（先判允许）。前缀匹配按模块边界处理，
  带点的前缀（如 `androidx.`）不会变成 `androidx..`。
- `symbolGuards`：`classes` 中的类名只允许出现在 `allowedPaths` 的路径 glob 内；
  扫描代码行时跳过注释行。
- 覆盖统计：每条规则输出 `eligible`（扫描文件数）/`matched`（pathPrefix 命中
  文件数）/`violations`；eligible 或 matched 为 0 → WARN（说明规则没扫到东西或
  前缀写错），WARN 不影响退出码；`--strict` 时 matched=0 升为 FAIL。
  符号守卫同样输出覆盖统计。
- 支持 Kotlin/Java `import` 与 Python `from x import` / `import x`。
- 违规逐条输出 `file:rule`，exit 1；仅 WARN 时 exit 0。

不写文件、不联网、无第三方依赖。
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CONFIG_REL = Path("harness") / "config.json"
DEFAULT_EXTENSIONS = (".kt", ".java", ".py")
DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        ".git", ".venv", "venv", "node_modules", "build", "dist", "__pycache__",
        ".mypy_cache", ".pytest_cache", ".tox", ".eggs", "target", ".idea", ".vscode",
    }
)
JAVA_IMPORT_RE = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)")
PY_FROM_RE = re.compile(r"^\s*from\s+([\w.]+)\s+import\b")
PY_IMPORT_RE = re.compile(r"^\s*import\s+(.+)$")


class ConfigError(Exception):
    """配置缺失 / 类型非法（可读报错 → exit 1）。"""


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def load_layers(root: Path) -> dict | None:
    path = root / CONFIG_REL
    if not path.is_file():
        raise ConfigError(f"缺少配置文件 {CONFIG_REL.as_posix()}（相对 {root}）")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{CONFIG_REL.as_posix()} 不是合法 JSON：{exc}") from exc
    if not isinstance(config, dict):
        raise ConfigError(f"{CONFIG_REL.as_posix()} 顶层必须是 JSON 对象")
    layers = config.get("layers")
    if layers is None:
        return None
    if not isinstance(layers, dict):
        raise ConfigError("config.layers 必须是对象")
    return layers


def relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"config.layers.{label} 缺失或不是非空字符串")
    cleaned = value.strip().replace("\\", "/")
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    candidate = Path(cleaned)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ConfigError(f"config.layers.{label} 必须是仓库相对路径（不允许绝对路径/..）：{value!r}")
    return cleaned


def string_list(value: object, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ConfigError(f"config.layers.{label} 必须是非空字符串数组")
    return list(value)


def normalize_extensions(layers: dict) -> tuple[str, ...]:
    raw = layers.get("extensions", list(DEFAULT_EXTENSIONS))
    if not isinstance(raw, list) or not raw or not all(isinstance(item, str) and item for item in raw):
        raise ConfigError("config.layers.extensions 必须是非空字符串数组")
    extensions: list[str] = []
    for item in raw:
        ext = item.strip().lower()
        if not ext.startswith("."):
            ext = "." + ext
        extensions.append(ext)
    return tuple(dict.fromkeys(extensions))


def normalize_excludes(layers: dict) -> list[str]:
    raw = layers.get("exclude", [])
    if not isinstance(raw, list):
        raise ConfigError("config.layers.exclude 必须是数组")
    excludes: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            raise ConfigError(f"config.layers.exclude[{index}] 必须是非空字符串")
        cleaned = item.strip().replace("\\", "/")
        if cleaned.startswith("./"):
            cleaned = cleaned[2:]
        if Path(cleaned).is_absolute() or ".." in Path(cleaned).parts:
            raise ConfigError(f"config.layers.exclude[{index}] 必须是仓库相对路径/glob：{item!r}")
        excludes.append(cleaned)
    return excludes


def normalize_rules(layers: dict) -> list[dict]:
    raw = layers.get("rules", [])
    if not isinstance(raw, list):
        raise ConfigError("config.layers.rules 必须是数组")
    rules: list[dict] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ConfigError(f"config.layers.rules[{index}] 必须是对象")
        name = item.get("name") or f"rule{index + 1}"
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(f"config.layers.rules[{index}].name 必须是非空字符串")
        prefix = relative_path(item.get("pathPrefix"), f"rules[{index}].pathPrefix")
        rules.append(
            {
                "name": name.strip(),
                "pathPrefix": prefix,
                "forbiddenImports": string_list(
                    item.get("forbiddenImports"), f"rules[{index}].forbiddenImports"
                ),
                "allowedImports": string_list(
                    item.get("allowedImports"), f"rules[{index}].allowedImports"
                ),
            }
        )
    return rules


def normalize_guards(layers: dict) -> list[dict]:
    raw = layers.get("symbolGuards", [])
    if not isinstance(raw, list):
        raise ConfigError("config.layers.symbolGuards 必须是数组")
    guards: list[dict] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ConfigError(f"config.layers.symbolGuards[{index}] 必须是对象")
        name = item.get("name") or f"symbolGuard{index + 1}"
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(f"config.layers.symbolGuards[{index}].name 必须是非空字符串")
        classes = string_list(item.get("classes"), f"symbolGuards[{index}].classes")
        if not classes:
            raise ConfigError(f"config.layers.symbolGuards[{index}].classes 不能为空")
        allowed = string_list(item.get("allowedPaths"), f"symbolGuards[{index}].allowedPaths")
        guards.append({"name": name.strip(), "classes": classes, "allowedPaths": allowed})
    return guards


def path_excluded(relative: str, excludes: list[str]) -> bool:
    """默认排除目录 / *.egg-info / layers.exclude（前缀或 glob）。"""
    parts = [part for part in relative.split("/") if part]
    if any(part in DEFAULT_EXCLUDED_DIRS for part in parts):
        return True
    if any(fnmatch.fnmatch(part, "*.egg-info") for part in parts):
        return True
    for entry in excludes:
        has_glob = any(char in entry for char in "*?[")
        normalized = entry.rstrip("/")
        if has_glob:
            if fnmatch.fnmatch(relative, entry) or fnmatch.fnmatch(parts[-1] if parts else "", entry):
                return True
        elif relative == normalized or relative.startswith(normalized + "/"):
            return True
    return False


def git_name_list(root: Path, *args: str) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args, "-z"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return [item for item in result.stdout.split("\0") if item]


def git_source_files(root: Path) -> tuple[list[str], list[str]] | None:
    """返回 (tracked, untracked) 源文件候选（未过滤 extensions/sourceRoot）。"""
    tracked = git_name_list(root, "ls-files")
    if tracked is None:
        return None
    untracked = git_name_list(root, "ls-files", "--others", "--exclude-standard") or []
    return tracked, untracked


def source_files(
    root: Path, source_root: str, extensions: tuple[str, ...], excludes: list[str]
) -> dict:
    """发现源文件：git 优先，回退文件系统；返回结构化发现结果。"""
    base = root / source_root
    if source_root != "." and not base.is_dir():
        raise ConfigError(f"源码目录不存在：{source_root}（config.layers.sourceRoot）")

    git_files = git_source_files(root)
    if git_files is not None:
        tracked, untracked = git_files
        entries: list[tuple[str, bool]] = [(rel, True) for rel in tracked] + [
            (rel, False) for rel in untracked
        ]
        candidates = [
            (relative, is_tracked)
            for relative, is_tracked in entries
            if (source_root == "." or relative.startswith(source_root.rstrip("/") + "/"))
            and Path(relative).suffix.lower() in extensions
        ]
        files = [
            relative
            for relative, _ in candidates
            if not path_excluded(relative, excludes)
        ]
        untracked_files = [
            relative
            for relative in files
            if relative in set(untracked)
        ]
        return {
            "source": "git",
            "files": sorted(files),
            "tracked": len([relative for relative in files if relative not in set(untracked)]),
            "untracked": len(untracked_files),
            "untrackedFiles": sorted(untracked_files),
            "excludedFiles": len(candidates) - len(files),
            "excludedDirs": 0,
        }

    files: list[str] = []
    excluded_files = 0
    excluded_dirs = 0
    walk_root = root if source_root == "." else base
    for dirpath, dirnames, filenames in os.walk(walk_root, topdown=True):
        current = Path(dirpath)
        relative_dir = current.relative_to(root).as_posix() if current != root else ""
        kept_dirs: list[str] = []
        for name in sorted(dirnames):
            relative = f"{relative_dir}/{name}" if relative_dir else name
            if path_excluded(relative, excludes):
                excluded_dirs += 1
                continue
            kept_dirs.append(name)
        dirnames[:] = kept_dirs
        for filename in sorted(filenames):
            if Path(filename).suffix.lower() not in extensions:
                continue
            relative = f"{relative_dir}/{filename}" if relative_dir else filename
            if path_excluded(relative, excludes):
                excluded_files += 1
                continue
            files.append(relative)
    return {
        "source": "filesystem",
        "files": sorted(files),
        "tracked": 0,
        "untracked": len(files),
        "untrackedFiles": [],
        "excludedFiles": excluded_files,
        "excludedDirs": excluded_dirs,
    }


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def code_lines(text: str) -> list[str]:
    """跳过整行注释与块注释内的行（够用即可，不追求完整语法解析）。"""
    lines: list[str] = []
    in_block = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if in_block:
            if "*/" in stripped:
                in_block = False
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block = True
            continue
        if stripped.startswith(("//", "#", "*", "<!--")):
            continue
        lines.append(raw)
    return lines


def imports_of(path: Path, lines: list[str]) -> list[str]:
    imports: list[str] = []
    if path.suffix.lower() == ".py":
        for line in lines:
            from_match = PY_FROM_RE.match(line)
            if from_match:
                module = from_match.group(1)
                if not module.startswith("."):
                    imports.append(module)
                continue
            import_match = PY_IMPORT_RE.match(line)
            if import_match:
                for token in import_match.group(1).split(","):
                    name = token.strip().split()[0] if token.strip() else ""
                    if name and not name.startswith("."):
                        imports.append(name)
        return imports
    for line in lines:
        match = JAVA_IMPORT_RE.match(line)
        if match:
            imports.append(match.group(1))
    return imports


def module_matches(imported: str, prefixes: list[str]) -> str | None:
    """按模块边界匹配前缀；`androidx.` 与 `androidx.foo` 都能命中前缀 `androidx.`。"""
    for prefix in prefixes:
        base = prefix.rstrip(".")
        if imported == base or imported.startswith(base + "."):
            return prefix
    return None


def matches_path_prefix(relative: str, prefix: str, source_root: str) -> bool:
    normalized = prefix.rstrip("/") + "/"
    if relative.startswith(normalized):
        return True
    root_prefix = source_root.rstrip("/") + "/"
    if source_root != "." and not normalized.startswith(root_prefix):
        return relative.startswith(root_prefix + normalized)
    return False


def allowed_path(relative: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(relative, pattern) for pattern in patterns)


def check_layers(root: Path, layers: dict, *, strict: bool = False) -> dict:
    """返回结构化结果：source/scanned/excludedFiles/excludedDirs/rules/guards/problems/warnings。"""
    source_root = relative_path(layers.get("sourceRoot"), "sourceRoot")
    rules = normalize_rules(layers)
    guards = normalize_guards(layers)
    extensions = normalize_extensions(layers)
    excludes = normalize_excludes(layers)
    discovery = source_files(root, source_root, extensions, excludes)
    files: list[str] = discovery["files"]

    # 每个文件只解析一次（import 供规则、代码行供符号守卫）。
    parsed: dict[str, tuple[list[str], str]] = {}
    for relative in files:
        try:
            text = (root / relative).read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        lines = code_lines(text)
        parsed[relative] = (imports_of(root / relative, lines), "\n".join(lines))

    problems: list[str] = []
    warnings: list[str] = []
    rule_stats: list[dict] = []
    for rule in rules:
        matched = 0
        violations = 0
        for relative in files:
            if not matches_path_prefix(relative, rule["pathPrefix"], source_root):
                continue
            matched += 1
            imports, _ = parsed[relative]
            for imported in imports:
                if module_matches(imported, rule["allowedImports"]):
                    continue
                hit = module_matches(imported, rule["forbiddenImports"])
                if hit:
                    violations += 1
                    problems.append(
                        f"{relative}:{rule['name']}: import {imported} 命中禁止前缀 {hit}"
                    )
        stat = {
            "name": rule["name"],
            "pathPrefix": rule["pathPrefix"],
            "eligible": len(files),
            "matched": matched,
            "violations": violations,
        }
        rule_stats.append(stat)
        if not files:
            message = (
                f"规则 {rule['name']} 未扫描到任何源文件"
                "（eligible=0；检查 sourceRoot/extensions/exclude）"
            )
            if strict:
                problems.append(f"严格模式：{message}")
            else:
                warnings.append(message)
        elif matched == 0:
            message = (
                f"规则 {rule['name']} 未匹配任何源文件"
                f"（matched=0；检查 pathPrefix={rule['pathPrefix']}）"
            )
            if strict:
                problems.append(f"严格模式：{message}")
            else:
                warnings.append(message)

    if discovery["untracked"]:
        warnings.append(
            f"存在 {discovery['untracked']} 个未跟踪源文件"
            "（本地会检查，但 CI 只覆盖 tracked；提交后请复跑）"
        )

    guard_stats: list[dict] = []
    for guard in guards:
        allowed_paths = guard["allowedPaths"]
        if not allowed_paths:
            guard_stats.append(
                {
                    "name": guard["name"],
                    "classes": guard["classes"],
                    "eligible": len(files),
                    "matched": 0,
                    "violations": 0,
                }
            )
            warnings.append(f"符号守卫 {guard['name']} 的 allowedPaths 为空，守卫未生效")
            continue
        eligible = 0
        matched = 0
        violations = 0
        for relative in files:
            if allowed_path(relative, allowed_paths):
                continue
            eligible += 1
            _, joined = parsed[relative]
            hits = [name for name in guard["classes"] if re.search(rf"\b{re.escape(name)}\b", joined)]
            if hits:
                matched += 1
                violations += len(hits)
                for name in hits:
                    problems.append(
                        f"{relative}:{guard['name']}: 符号 {name} 只允许出现在 "
                        + "、".join(allowed_paths)
                    )
        guard_stats.append(
            {
                "name": guard["name"],
                "classes": guard["classes"],
                "eligible": eligible,
                "matched": matched,
                "violations": violations,
            }
        )
        if eligible == 0:
            warnings.append(
                f"符号守卫 {guard['name']} 未覆盖任何文件（eligible=0；检查 allowedPaths）"
            )

    return {
        "source": discovery["source"],
        "sourceRoot": source_root,
        "scanned": len(files),
        "tracked": discovery["tracked"],
        "untracked": discovery["untracked"],
        "untrackedFiles": discovery["untrackedFiles"],
        "files": files,
        "excludedFiles": discovery["excludedFiles"],
        "excludedDirs": discovery["excludedDirs"],
        "rules": rule_stats,
        "guards": guard_stats,
        "problems": problems,
        "warnings": warnings,
    }


def _source_label(source: str) -> str:
    return "git 跟踪（git ls-files）" if source == "git" else "文件系统遍历（非 git 回退）"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="通用分层守卫（配置驱动 imports / symbols）")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="项目根（默认脚本上级目录）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="规则 matched=0 时升为 FAIL（接入/发布门禁用）",
    )
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        fail(f"根目录不存在：{root}")
        return 1

    try:
        layers = load_layers(root)
    except ConfigError as exc:
        fail(f"配置不可用：{exc}")
        return 1

    if layers is None:
        print("[SKIP] 未配置 layers（harness/config.json），跳过分层检查")
        return 0

    try:
        result = check_layers(root, layers, strict=args.strict)
    except ConfigError as exc:
        fail(f"配置不可用：{exc}")
        return 1

    for problem in result["problems"]:
        fail(problem)
    for warning in result["warnings"]:
        print(f"[WARN] {warning}")
    print(
        f"[OK] 分层检查来源：{_source_label(result['source'])}｜"
        f"扫描 {result['scanned']} 个源文件"
        f"（tracked {result['tracked']} / untracked {result['untracked']}；"
        f"排除 {result['excludedFiles']} 个文件 / {result['excludedDirs']} 个目录）"
    )
    for stat in result["rules"]:
        print(
            f"[OK]   规则 {stat['name']}：eligible={stat['eligible']} "
            f"matched={stat['matched']} violations={stat['violations']}"
        )
    for guard in result["guards"]:
        print(
            f"[OK]   符号守卫 {guard['name']}：eligible={guard['eligible']} "
            f"matched={guard['matched']} violations={guard['violations']}"
        )
    if result["problems"]:
        print(f"[FAIL] check_layers 发现 {len(result['problems'])} 个分层问题（exit 1）")
        return 1
    print(
        f"[OK] 分层检查：{len(result['rules'])} 条规则、"
        f"{len(result['guards'])} 个符号守卫，0 违规"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
