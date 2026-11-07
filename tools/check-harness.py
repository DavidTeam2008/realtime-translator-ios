#!/usr/bin/env python3
"""指令层机检：token 预算 / 嵌套 AGENTS / 敏感信息 / § 引用漂移 / skills。

用法：
    python3 tools/check-harness.py [--root PATH]
默认 root 为脚本上级目录（仓库根）。依赖 Phase 0 的：
    tools/token_estimate.py     —— estimate_tokens(text) -> int
    tools/rules-budget.json     —— 见下（Lead 维护；本脚本只读）
        {
          "estimator": "...",
          "tokenBudgets": {"AGENTS.md": 1600, "references/contracts.md": 950, ...},
          "nestedAgents": {"maxBytes": 8192, "files": ["harness/AGENTS.md", ...]},
          "skills": {"root": ".dsh/skills", "requiredFields": ["name", "description"],
                     "namePattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"}
        }

检查项：
    1. tokenBudgets 中每个文件存在且 estimate_tokens ≤ 预算
    2. nestedAgents.files 中每个嵌套 AGENTS 存在且字节数 ≤ maxBytes
    3. 根/嵌套 AGENTS 与 .dsh/skills 不得出现 /Users/、UDID/UUID、sk- 密钥
    4. 指令文件（根 AGENTS.md + nestedAgents.files + .dsh/skills/*/SKILL.md）的
       §/第N节 引用能命中目标文件与对应编号标题（范围校验两端）；支持 `§N`/`§N–§M`、
       `第 N 节`/`第N节`/`第 N–M 节`。目标按优先级解析：同一行 match 之前最近的
       .md 路径 token（相对被扫描文件目录，再回退根目录/常见目录）→ 唯一文档简写
       （如 `docs/02`）→ 行内「根 AGENTS」→ 根 AGENTS.md 自引用；都解析不到则 FAIL。
    5. 根 AGENTS.md 提到的仓库内 .md 文件必须存在
    6. .dsh/skills/* 存在时校验 YAML frontmatter（name kebab-case / description 非空）
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
BUDGET_REL = "tools/rules-budget.json"
DEFAULT_NESTED_MAX_BYTES = 8192
DEFAULT_SKILLS_ROOT = ".dsh/skills"
DEFAULT_REQUIRED_FIELDS = ("name", "description")
DEFAULT_NAME_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"

# 不在版本库 / 允许不存在的机器本地文件（AGENTS.md 只写“如存在”）。
OPTIONAL_MD_PATHS = frozenset({"AGENTS.local.md", "CLAUDE.local.md"})
# 裸文件名解析兜底目录（AGENTS.md 常写 `contracts.md` 这类简写）。
BARE_NAME_FALLBACK_DIRS = ("docs", "references", "harness", "harness/plans")

SENSITIVE_PATTERNS = (
    ("绝对路径 /Users/", re.compile(r"/Users/")),
    (
        "UDID/UUID（十六进制连字符）",
        re.compile(
            r"\b[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\b"
            r"|\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{8,16}\b"
            r"|\b[0-9A-Fa-f]{40}\b"
        ),
    ),
    ("疑似密钥（sk-）", re.compile(r"(?:^|[^A-Za-z0-9_])sk-[A-Za-z0-9_\-]{8,}")),
)

URL_RE = re.compile(r"https?://\S+")
SECTION_RE = re.compile(r"§\s*(\d+(?:\.\d+)?)(?:\s*[–—~-]\s*§?\s*(\d+(?:\.\d+)?))?")
# 「第 7 节」「第3节」「第 3–4 节」「第 3–第 4 节」；范围只校验给出的编号两端。
CN_SECTION_RE = re.compile(
    r"第\s*(\d+(?:\.\d+)?)\s*(?:[–—~-]\s*(?:第\s*)?(\d+(?:\.\d+)?))?\s*节"
)
MD_PATH_RE = re.compile(r"[A-Za-z0-9_.\-/]+\.md")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
# 文档简写（如 `docs/02`）：无 .md 后缀，按唯一前缀解析到具体文件。
SHORTHAND_RE = re.compile(r"^(?:\.\./)*(?:docs|references|harness)/[A-Za-z0-9_.\-/]+$")
SECTION_PATTERNS = ((SECTION_RE, "§"), (CN_SECTION_RE, "第N节"))


class Report:
    """收集逐项结果；problem 计入 exit 1。"""

    def __init__(self) -> None:
        self.problems: list[str] = []
        self.checks = 0

    def ok(self, message: str) -> None:
        self.checks += 1
        print(f"[OK] {message}")

    def skip(self, message: str) -> None:
        print(f"[SKIP] {message}")

    def warn(self, message: str) -> None:
        print(f"[WARN] {message}")

    def fail(self, message: str) -> None:
        self.checks += 1
        self.problems.append(message)
        print(f"[FAIL] {message}")


def load_budget(root: Path, report: Report) -> dict:
    path = root / BUDGET_REL
    if not path.is_file():
        report.fail(f"缺少 {BUDGET_REL}（Lead 提供；无法校验预算/嵌套 AGENTS/skills）")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.fail(f"{BUDGET_REL} 不是合法 JSON：{exc}")
        return {}
    if not isinstance(data, dict):
        report.fail(f"{BUDGET_REL} 顶层必须是对象")
        return {}
    return data


def load_estimator(root: Path):
    """优先用 root/tools/token_estimate.py（fixture 自包含），回退脚本同目录。"""
    candidates = [root / "tools" / "token_estimate.py", Path(__file__).resolve().parent / "token_estimate.py"]
    seen: set[Path] = set()
    for candidate in candidates:
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            spec = importlib.util.spec_from_file_location("_duiyi_token_estimate", candidate)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            estimator = getattr(module, "estimate_tokens", None)
            if callable(estimator):
                return estimator
        except Exception:  # noqa: BLE001 - 估算器坏了按缺失处理并报 FAIL
            continue
    return None


def check_token_budgets(root: Path, data: dict, estimator, report: Report) -> None:
    budgets = data.get("tokenBudgets")
    if not isinstance(budgets, dict) or not budgets:
        report.fail(f"{BUDGET_REL}.tokenBudgets 缺失或为空")
        return
    if estimator is None:
        report.fail("缺少可用的 tools/token_estimate.py（estimate_tokens）")
        return
    for rel, budget in sorted(budgets.items()):
        if not isinstance(rel, str) or not isinstance(budget, int):
            report.fail(f"{BUDGET_REL}.tokenBudgets 项非法：{rel!r} -> {budget!r}")
            continue
        path = root / rel
        if not path.is_file():
            report.fail(f"token 预算登记的文件不存在：{rel}")
            continue
        tokens = estimator(path.read_text(encoding="utf-8", errors="replace"))
        if tokens > budget:
            report.fail(f"token 超预算：{rel} ≈{tokens} > {budget}（超 {tokens - budget}）")
        else:
            report.ok(f"token {rel}：≈{tokens}/{budget}（余 {budget - tokens}）")


def nested_agent_files(root: Path, data: dict, report: Report) -> list[str]:
    """校验嵌套 AGENTS 的存在性与字节上限；返回相对路径列表（供敏感扫描）。"""
    config = data.get("nestedAgents")
    if not isinstance(config, dict):
        report.fail(f"{BUDGET_REL}.nestedAgents 缺失")
        return []
    default_max = config.get("maxBytes", DEFAULT_NESTED_MAX_BYTES)
    entries = config.get("files")
    if not isinstance(entries, list) or not entries:
        report.fail(f"{BUDGET_REL}.nestedAgents.files 缺失或为空")
        return []
    if not isinstance(default_max, int) or default_max <= 0:
        report.fail(f"{BUDGET_REL}.nestedAgents.maxBytes 非法：{default_max!r}")
        return []
    rel_paths: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            rel, max_bytes = entry, default_max
        elif isinstance(entry, dict):
            rel = entry.get("path") or entry.get("file")
            max_bytes = entry.get("maxBytes", default_max)
        else:
            report.fail(f"{BUDGET_REL}.nestedAgents.files 项非法：{entry!r}")
            continue
        if not isinstance(rel, str) or not rel:
            report.fail(f"{BUDGET_REL}.nestedAgents.files 项缺少 path：{entry!r}")
            continue
        if not isinstance(max_bytes, int) or max_bytes <= 0:
            report.fail(f"嵌套 AGENTS 的 maxBytes 非法：{rel} -> {max_bytes!r}")
            continue
        path = root / rel
        rel_paths.append(rel)
        if not path.is_file():
            report.fail(f"缺少嵌套 AGENTS：{rel}")
            continue
        size = path.stat().st_size
        lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        if size > max_bytes:
            report.fail(f"嵌套 AGENTS 超长：{rel} {size} > {max_bytes} bytes")
        else:
            report.ok(f"nested {rel}：{size}/{max_bytes} bytes（{lines} 行）")
    return rel_paths


def skill_files(root: Path, data: dict) -> list[tuple[Path, str]]:
    """返回 [(skill 文件路径, 相对 root 的展示名)]。"""
    config = data.get("skills")
    if not isinstance(config, dict):
        config = {}
    skills_root = root / (config.get("root") or DEFAULT_SKILLS_ROOT)
    if not skills_root.is_dir():
        return []
    files: list[Path] = []
    files += sorted(skills_root.glob("*/SKILL.md"))
    files += sorted(skills_root.glob("*.md"))
    return [(path, path.relative_to(root).as_posix()) for path in files]


def check_sensitive(root: Path, agents_rel: str, nested_rel_paths: list[str],
                    skills: list[tuple[Path, str]], report: Report) -> None:
    targets: list[Path] = []
    agents = root / agents_rel
    if agents.is_file():
        targets.append(agents)
    for rel in nested_rel_paths:
        path = root / rel
        if path.is_file():
            targets.append(path)
    targets += [path for path, _ in skills]
    scanned = 0
    hits = 0
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        rel = path.relative_to(root).as_posix()
        for label, pattern in SENSITIVE_PATTERNS:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                report.fail(f"敏感信息 {rel}:{line}: {label}（{match.group(0)}）")
                hits += 1
    if hits == 0:
        report.ok(f"敏感信息：扫描 {scanned} 个指令文件，0 命中")


def resolve_md_path(root: Path, token: str, base: Path | None = None) -> Path | None:
    """解析 .md 路径 token：优先相对被扫描文件目录（base），再回退根目录/常见目录。"""
    token = token.replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    if token.startswith("/"):
        return None
    directories = (base, root) if base is not None else (root,)
    candidates = [directory / token for directory in directories]
    if "/" not in token:
        candidates += [root / directory / token for directory in BARE_NAME_FALLBACK_DIRS]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def nearest_shorthand(text_before: str) -> str | None:
    """取 §/第N节 之前最近的文档简写 token（反引号包裹，如 `docs/02`）。"""
    for match in reversed(list(INLINE_CODE_RE.finditer(text_before))):
        token = match.group(1).strip().rstrip("/")
        if not token or token.endswith(".md"):
            continue
        if SHORTHAND_RE.match(token):
            return token
    return None


def resolve_shorthand(root: Path, token: str, base: Path | None = None) -> Path | None:
    """把文档简写解析成唯一文件：`docs/02` → docs/02-architecture.md；多义则 None。"""
    token = token.replace("\\", "/").strip().rstrip("/")
    directories = [base, root] if base is not None else [root]
    hits: list[Path] = []
    for directory in directories:
        for candidate in (directory / token, directory / (token + ".md")):
            if candidate.is_file() and candidate not in hits:
                hits.append(candidate)
        for candidate in sorted(directory.glob(token + "*.md")):
            if candidate not in hits:
                hits.append(candidate)
    return hits[0].resolve() if len(hits) == 1 else None


def has_heading(text: str, number: str) -> bool:
    pattern = re.compile(rf"^#{{1,6}}\s*{re.escape(number)}(?:[.．]|\s|$)", re.M)
    return pattern.search(text) is not None


def section_ref_files(root: Path, nested_rel_paths: list[str],
                      skills: list[tuple[Path, str]]) -> list[Path]:
    """§/第N节 扫描对象：根 AGENTS + 嵌套 AGENTS + skills（去重，只取存在文件）。"""
    candidates: list[Path] = []
    agents = root / "AGENTS.md"
    if agents.is_file():
        candidates.append(agents)
    candidates += [root / rel for rel in nested_rel_paths]
    candidates += [path for path, _ in skills]
    files: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        files.append(path)
    return files


def ref_label(kind: str, number: str) -> str:
    return f"§{number}" if kind == "§" else f"第 {number} 节"


def locate_section_target(root: Path, scanned: Path, line: str, start: int,
                          kind: str) -> tuple[Path | None, str | None]:
    """按优先级定位一条 §/第N节 引用的目标文件；返回 (target, error)。"""
    # a) 同一行 match 之前最近的 .md 路径 token（保留既有逻辑；嵌套文件先按自身目录解析）
    md_tokens = list(MD_PATH_RE.finditer(line[:start]))
    if md_tokens:
        token = md_tokens[-1].group(0)
        target = resolve_md_path(root, token, base=scanned.parent)
        if target is None:
            return None, f"引用目标文件不存在：{token}"
        return target, None
    # a′) 文档简写（如 `docs/02`）：仅在唯一解析到文件时接受（真实仓库嵌套 AGENTS 用法）
    shorthand = nearest_shorthand(line[:start])
    if shorthand is not None:
        target = resolve_shorthand(root, shorthand, base=scanned.parent)
        if target is None:
            return None, f"引用目标文件不存在或无法唯一解析：{shorthand}"
        return target, None
    # b) 行内出现「根 AGENTS」→ 根 AGENTS.md
    if "根 AGENTS" in line:
        target = root / "AGENTS.md"
        if target.is_file():
            return target, None
        return None, "引用目标文件不存在：AGENTS.md"
    # c) 被扫描文件就是根 AGENTS.md → 自引用（如「覆盖只写第 7 节」）
    if scanned.resolve() == (root / "AGENTS.md").resolve():
        return scanned, None
    return None, "无法定位 §/第N节 引用目标"


def check_section_refs(root: Path, files: list[Path], report: Report) -> None:
    checked = 0
    failed = 0
    hit_files: set[Path] = set()
    for scanned in files:
        display = scanned.relative_to(root).as_posix()
        text = scanned.read_text(encoding="utf-8", errors="replace")
        for lineno, raw in enumerate(text.splitlines(), 1):
            line = URL_RE.sub(" ", raw)
            matches: list[tuple[int, str, re.Match[str]]] = []
            for pattern, kind in SECTION_PATTERNS:
                for match in pattern.finditer(line):
                    matches.append((match.start(), kind, match))
            for start, kind, match in sorted(matches, key=lambda item: item[0]):
                numbers = [group for group in match.groups() if group]
                target, error = locate_section_target(root, scanned, line, start, kind)
                if error is not None:
                    report.fail(f"{display}:{lineno}: {error}（原文：{match.group(0)}）")
                    failed += 1
                    continue
                assert target is not None
                checked += 1
                hit_files.add(scanned)
                try:
                    target_display = target.relative_to(root).as_posix()
                except ValueError:
                    target_display = target.name
                target_text = target.read_text(encoding="utf-8", errors="replace")
                missing = [number for number in numbers if not has_heading(target_text, number)]
                if missing:
                    holes = "、".join(ref_label(kind, number) for number in missing)
                    report.fail(f"{display}:{lineno}: {target_display} 缺少 {holes} 对应的编号标题")
                    failed += 1
    scanned_count = len(files)
    if failed:
        report.fail(f"§/第N节 引用：通过 {checked} 处、失败 {failed} 处（扫描 {scanned_count} 个指令文件）")
    elif checked:
        report.ok(
            f"§/第N节 引用：{checked} 处命中（{len(hit_files)} 个指令文件，扫描 {scanned_count} 个）"
        )
    else:
        report.warn(
            f"§/第N节 引用：扫描 {scanned_count} 个指令文件，0 处命中（疑似空转：检查引用语法是否变化）"
        )


def check_mentioned_paths(root: Path, agents: Path, report: Report) -> None:
    lines = agents.read_text(encoding="utf-8", errors="replace").splitlines()
    seen: set[str] = set()
    checked = 0
    failed = 0
    for lineno, raw in enumerate(lines, 1):
        line = URL_RE.sub(" ", raw)
        for match in MD_PATH_RE.finditer(line):
            token = match.group(0)
            while token.startswith("./"):
                token = token[2:]
            if token in OPTIONAL_MD_PATHS or token in seen:
                continue
            seen.add(token)
            if resolve_md_path(root, token) is None:
                report.fail(f"{agents.name}:{lineno}: 引用的文件不存在：{token}")
                failed += 1
            else:
                checked += 1
    if failed == 0:
        report.ok(f"引用文件存在性：{checked} 个仓库内 .md 引用全部存在")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields: dict[str, str] = {}
    current: str | None = None
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key_match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if key_match:
            current = key_match.group(1)
            value = key_match.group(2).strip()
            fields[current] = "" if value in {"|", ">", "|-", ">-", "|+", ">+"} else value.strip("'\"")
        elif current and line.startswith((" ", "\t")):
            fields[current] = (fields.get(current, "") + " " + line.strip()).strip()
        elif line.strip():
            return None
    return None


def check_skills(root: Path, data: dict, report: Report) -> None:
    config = data.get("skills") if isinstance(data.get("skills"), dict) else {}
    skills_root_rel = config.get("root") or DEFAULT_SKILLS_ROOT
    required = config.get("requiredFields") or list(DEFAULT_REQUIRED_FIELDS)
    name_pattern = re.compile(config.get("namePattern") or DEFAULT_NAME_PATTERN)
    skills = skill_files(root, data)
    if not skills:
        report.skip(f"skills：{skills_root_rel} 不存在或无 SKILL.md（Phase 1 引入，SKIP）")
        return
    for path, display in skills:
        text = path.read_text(encoding="utf-8", errors="replace")
        fields = parse_frontmatter(text)
        if fields is None:
            report.fail(f"skill {display}：缺少合法 YAML frontmatter（--- 包裹）")
            continue
        missing = [field for field in required if not fields.get(field, "").strip()]
        if missing:
            report.fail(f"skill {display}：frontmatter 缺字段 {', '.join(missing)}")
            continue
        name = fields["name"].strip()
        if not name_pattern.match(name):
            report.fail(f"skill {display}：name={name!r} 不是 kebab-case")
            continue
        report.ok(f"skill {display}：name={name}，description {len(fields['description'])} 字符")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="指令层机检（预算/嵌套 AGENTS/引用/skills/敏感信息）")
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="仓库根（默认脚本上级目录，用于 fixture 测试）",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    report = Report()

    print("check-harness · 指令层机检")
    agents = root / "AGENTS.md"
    if not agents.is_file():
        report.fail("缺少根 AGENTS.md")
    data = load_budget(root, report)
    estimator = load_estimator(root)

    nested_rel_paths: list[str] = []
    if data:
        check_token_budgets(root, data, estimator, report)
        nested_rel_paths = nested_agent_files(root, data, report)
    skills = skill_files(root, data)
    if agents.is_file():
        check_sensitive(root, "AGENTS.md", nested_rel_paths, skills, report)
        check_section_refs(root, section_ref_files(root, nested_rel_paths, skills), report)
        check_mentioned_paths(root, agents, report)
    check_skills(root, data, report)

    if report.problems:
        print(f"[FAIL] check-harness 未通过：{len(report.problems)} 个问题（exit 1）")
        return 1
    print(f"[PASS] check-harness 通过（{report.checks} 项检查）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
