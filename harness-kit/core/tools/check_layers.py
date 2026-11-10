#!/usr/bin/env python3
"""通用分层守卫（配置驱动；标准库；不联网）。

用法：
    python3 tools/check_layers.py [--root PATH]

根目录默认「本脚本上级目录」；`--root` 可覆盖。配置唯一来源是
`<root>/harness/config.json` 的 `layers` 段（**可选**）：

    "layers": {
      "sourceRoot": "src",
      "extensions": [".kt", ".java", ".py"],
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
- `rules`：对 `pathPrefix` 下的源文件，`forbiddenImports` 命中即违规；
  `allowedImports` 可覆盖（先判允许）。前缀匹配按模块边界处理，
  带点的前缀（如 `androidx.`）不会变成 `androidx..`。
- `symbolGuards`：`classes` 中的类名只允许出现在 `allowedPaths` 的路径 glob 内；
  扫描代码行时跳过注释行。
- 支持 Kotlin/Java `import` 与 Python `from x import` / `import x`。
- 违规逐条输出 `file:rule`，exit 1。

不写文件、不联网、无第三方依赖。
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

CONFIG_REL = Path("harness") / "config.json"
DEFAULT_EXTENSIONS = (".kt", ".java", ".py")
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


def source_files(root: Path, source_root: str, extensions: tuple[str, ...]) -> list[Path]:
    base = root / source_root
    if not base.is_dir():
        raise ConfigError(f"源码目录不存在：{source_root}（config.layers.sourceRoot）")
    files: set[Path] = set()
    for extension in extensions:
        files.update(path for path in base.rglob("*" + extension) if path.is_file())
    return sorted(files)


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
    if not normalized.startswith(root_prefix):
        return relative.startswith(root_prefix + normalized)
    return False


def allowed_path(relative: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(relative, pattern) for pattern in patterns)


def check_layers(root: Path, layers: dict) -> tuple[list[str], int]:
    source_root = relative_path(layers.get("sourceRoot"), "sourceRoot")
    rules = normalize_rules(layers)
    guards = normalize_guards(layers)
    extensions = normalize_extensions(layers)
    files = source_files(root, source_root, extensions)

    problems: list[str] = []
    for path in files:
        relative = rel(root, path)
        lines = code_lines(path.read_text(encoding="utf-8", errors="replace"))
        imports = imports_of(path, lines)

        for rule in rules:
            if not matches_path_prefix(relative, rule["pathPrefix"], source_root):
                continue
            for imported in imports:
                if module_matches(imported, rule["allowedImports"]):
                    continue
                hit = module_matches(imported, rule["forbiddenImports"])
                if hit:
                    problems.append(
                        f"{relative}:{rule['name']}: import {imported} 命中禁止前缀 {hit}"
                    )

        if guards:
            joined = "\n".join(lines)
            for guard in guards:
                if not guard["allowedPaths"] or allowed_path(relative, guard["allowedPaths"]):
                    continue
                for name in guard["classes"]:
                    if re.search(rf"\b{re.escape(name)}\b", joined):
                        problems.append(
                            f"{relative}:{guard['name']}: 符号 {name} 只允许出现在 "
                            + "、".join(guard["allowedPaths"])
                        )
    return problems, len(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="通用分层守卫（配置驱动 imports / symbols）")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="项目根（默认脚本上级目录）",
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
        problems, file_count = check_layers(root, layers)
    except ConfigError as exc:
        fail(f"配置不可用：{exc}")
        return 1

    if problems:
        for problem in problems:
            fail(problem)
        print(f"[FAIL] check_layers 发现 {len(problems)} 个分层问题（exit 1）")
        return 1
    rule_count = len(layers.get("rules") or [])
    guard_count = len(layers.get("symbolGuards") or [])
    print(
        f"[OK] 分层检查：{file_count} 个源文件、{rule_count} 条规则、"
        f"{guard_count} 个符号守卫，0 违规"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
