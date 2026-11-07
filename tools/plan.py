#!/usr/bin/env python3
"""跨会话计划：新建、状态机校验、交接摘要、接手与收尾（标准库实现，无第三方依赖）。

用法（在仓库根）：
  PYTHONDONTWRITEBYTECODE=1 python3 tools/plan.py new <topic>
  PYTHONDONTWRITEBYTECODE=1 python3 tools/plan.py latest [--active]
  PYTHONDONTWRITEBYTECODE=1 python3 tools/plan.py brief [计划路径]
  PYTHONDONTWRITEBYTECODE=1 python3 tools/plan.py check
  PYTHONDONTWRITEBYTECODE=1 python3 tools/plan.py resume
  PYTHONDONTWRITEBYTECODE=1 python3 tools/plan.py end

可选 `--root <repo>` 指定仓库根（默认脚本上级目录）。

计划头 front matter 用极简 YAML（不引入 PyYAML），只支持：
  key: value
  key: [a, b, c]
  key:
    - item
  scope:
    allow:
      - path/
    deny:
      - path/

字段：id / status / level / owner / updated / submitted，
      scope.allow / scope.deny / acceptance / verify。
status 只取 active | done | blocked | archived。

无 front matter 的旧计划按 legacy 处理：mtime 兜底 + WARN，不直接失败。

验证证据（check）：表头须含「证据ID」；证据 id 必须对应 harness/evidence/<id>.json 且
verdict=PASS；结果声称完成（PASS/通过/SUCCEEDED/已验证/已完成）时必须绑定可解析证据ID，
或使用白名单占位（基线/过程/外部/历史/未验证/负向）；done 计划必须有 submitted，
且被引用证据的 git.commit 绑定 HEAD 或 submitted。

退出码：0 = 通过（允许 WARN）；1 = 校验失败 / 缺少 active 计划；2 = 用法错误。
"""
from __future__ import annotations

import datetime as dt
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANS = ROOT / "harness" / "plans"
TEMPLATE = PLANS / "_template.md"

VALID_STATUS = ("active", "done", "blocked", "archived")
EVIDENCE_COLS = ("命令", "结果", "环境")


def set_root(value: str | Path) -> None:
    """切换仓库根（仅供 --root；Makefile 默认不传）。"""
    global ROOT, PLANS, TEMPLATE
    ROOT = Path(value).expanduser().resolve()
    PLANS = ROOT / "harness" / "plans"
    TEMPLATE = PLANS / "_template.md"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# 极简 front matter 解析
# ---------------------------------------------------------------------------

def split_front_matter(text: str) -> tuple[str | None, str]:
    """返回 (front matter 块, 正文)；没有 front matter 时返回 (None, 全文)。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1:])
    return None, text


def _strip_comment(value: str) -> str:
    # 行内注释与以 # 开头的整行注释都要剥掉；否则 `allow: # comment` 会被当成路径
    return re.sub(r"(?:^|\s+)#.*$", "", value).rstrip()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1].strip()
    return value


def _split_inline_list(value: str) -> list[str]:
    inner = value.strip()
    if not (inner.startswith("[") and inner.endswith("]")):
        return [inner] if inner else []
    inner = inner[1:-1].strip()
    if not inner:
        return []
    return [_unquote(item.strip()) for item in inner.split(",") if item.strip()]


def parse_front_matter(block: str) -> dict:
    """极简 YAML：顶层 key: value、一层嵌套 scope.allow/deny、- 列表与 [a, b]。"""
    meta: dict = {}
    top: str | None = None
    current_list: str | None = None
    for raw in block.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if stripped.startswith("- "):
            item = _unquote(_strip_comment(stripped[2:].strip()))
            if current_list is not None:
                meta.setdefault(current_list, [])
                if isinstance(meta[current_list], list):
                    meta[current_list].append(item)
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$", stripped)
        if not match:
            current_list = None
            continue
        key = match.group(1)
        value = _strip_comment(match.group(2)).strip()
        if indent == 0:
            top = key
            if not value:
                meta[key] = []
                current_list = key
            elif value.startswith("[") and value.endswith("]"):
                meta[key] = _split_inline_list(value)
                current_list = None
            else:
                meta[key] = _unquote(value)
                current_list = None
        else:
            if top is None:
                continue
            full = f"{top}.{key}"
            if not value:
                meta[full] = []
                current_list = full
            elif value.startswith("[") and value.endswith("]"):
                meta[full] = _split_inline_list(value)
                current_list = None
            else:
                meta[full] = _unquote(value)
                current_list = None
    # scope: 这类映射父键不应残留空列表
    for key in [k for k, v in meta.items() if v == [] and any(o.startswith(k + ".") for o in meta)]:
        del meta[key]
    return meta


def meta_list(meta: dict, key: str) -> list[str]:
    value = meta.get(key)
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


# ---------------------------------------------------------------------------
# 正文分节
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def normalize_title(title: str) -> str:
    text = re.sub(r"^\d+(?:\.\d+)*[.、)]?\s*", "", title.strip())
    text = re.sub(r"\s*[（(][^（）()]*[）)]\s*$", "", text).strip()
    return text


@dataclass
class Section:
    level: int
    title: str
    norm: str
    start: int  # 标题所在行号（相对正文）
    end: int    # 下一个同级/更高级标题的行号（或正文末尾）


def parse_sections(body: str) -> list[Section]:
    lines = body.splitlines()
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).strip()))
    sections: list[Section] = []
    for pos, (start, level, title) in enumerate(headings):
        end = len(lines)
        for later_pos in range(pos + 1, len(headings)):
            if headings[later_pos][1] <= level:
                end = headings[later_pos][0]
                break
        sections.append(Section(level, title, normalize_title(title), start, end))
    return sections


def find_section(sections: list[Section], keywords: tuple[str, ...] | list[str]) -> Section | None:
    """按 keyword 顺序找节：先精确标题，再前缀，再包含。"""
    for keyword in keywords:
        needle = keyword.lower()
        for matcher in (
            lambda norm: norm == needle,
            lambda norm: norm.startswith(needle),
            lambda norm: needle in norm,
        ):
            for sec in sections:
                if matcher(sec.norm.lower()):
                    return sec
    return None


# ---------------------------------------------------------------------------
# 计划文件
# ---------------------------------------------------------------------------

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
    "- 非目标：",
    "- 验收：",
    "- 验收（可执行判据）：",
    "（未运行 / 未取得证据的项；没有则写“无”）",
}


def is_placeholder(line: str) -> bool:
    stripped = line.strip()
    if stripped in PLACEHOLDERS:
        return True
    if stripped.startswith("<") and stripped.endswith(">"):
        return True
    if re.fullmatch(r"(无|暂无|N/A|TODO|待填|待补|待确认|待定)[。.]?", stripped):
        return True
    return False


def _dedent(lines: list[str]) -> list[str]:
    indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
    if not indents:
        return lines
    cut = min(indents)
    return [line[cut:] if line.strip() else "" for line in lines]


def section_raw_lines(plan: "Plan", sec: Section) -> list[str]:
    lines = plan.body.splitlines()[sec.start + 1: sec.end]
    return _dedent(lines)


def section_raw(plan: "Plan", sec: Section) -> str:
    return "\n".join(section_raw_lines(plan, sec)).strip("\n")


def section_text(plan: "Plan", sec: Section | None) -> str:
    """去掉占位行后的正文（用于“非空”判断与打印）。"""
    if sec is None:
        return ""
    kept = []
    for line in section_raw_lines(plan, sec):
        stripped = line.strip()
        if not stripped:
            continue
        if re.fullmatch(r"<!--.*-->", stripped):
            continue
        if stripped in ("---", "***", "___"):  # 分隔线不进入摘要
            continue
        if is_placeholder(stripped):
            continue
        kept.append(line.rstrip())
    return "\n".join(kept).strip()


@dataclass
class Plan:
    path: Path
    text: str
    body: str
    meta: dict = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)
    legacy: bool = False

    @property
    def status(self) -> str | None:
        value = self.meta.get("status")
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip().lower()

    def section(self, *keywords: str) -> Section | None:
        return find_section(self.sections, list(keywords))

    def section_text(self, *keywords: str) -> str:
        return section_text(self, self.section(*keywords))

    def sort_key(self) -> tuple:
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            mtime = 0.0
        updated = self.meta.get("updated")
        return (updated if isinstance(updated, str) else "", mtime, self.path.name)


def read_plan(path: Path) -> Plan:
    text = path.read_text(encoding="utf-8")
    block, body = split_front_matter(text)
    meta = parse_front_matter(block) if block is not None else {}
    return Plan(path=path, text=text, body=body, meta=meta,
                sections=parse_sections(body), legacy=block is None)


def plan_files() -> list[Path]:
    """`harness/plans/*.md`，跳过模板与 `_archive/`（glob 本身不递归到子目录）。"""
    if not PLANS.is_dir():
        return []
    return sorted(p for p in PLANS.glob("*.md") if p.name != "_template.md")


def load_plans() -> list[Plan]:
    return [read_plan(path) for path in plan_files()]


def resolve_plan_arg(arg: str | None) -> Plan:
    if not arg:
        return require_active_plan()
    path = Path(arg)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        sys.exit(f"[FAIL] 计划不存在：{arg}")
    return read_plan(path)


def active_plans(plans: list[Plan]) -> list[Plan]:
    return [plan for plan in plans if plan.status == "active"]


def require_active_plan() -> Plan:
    plans = load_plans()
    active = active_plans(plans)
    if not active:
        sys.exit(
            "[FAIL] 没有 active 计划（front matter status: active）。\n"
            "       用 `python3 tools/plan.py new <topic>` 新建，或 `latest` 查看历史计划；"
            "旧计划可补 status: done。"
        )
    if len(active) > 1:
        names = "、".join(rel(plan.path) for plan in sorted(active, key=lambda p: p.sort_key()))
        print(f"[WARN] 检测到 {len(active)} 个 active 计划（协议：一次只做一个 active）：{names}", file=sys.stderr)
    return max(active, key=Plan.sort_key)


# ---------------------------------------------------------------------------
# git 交叉比对
# ---------------------------------------------------------------------------

def git(args: list[str]) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git", *args], cwd=ROOT, text=True, capture_output=True, timeout=20
        )
        return result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:  # git 缺失/超时
        return 127, "", str(exc)


def git_status_paths() -> set[str] | None:
    """`git status --porcelain -z -uall` 中的路径集合；git 不可用时返回 None。"""
    code, out, _ = git(["status", "--porcelain", "-z", "--untracked-files=all"])
    if code != 0:
        return None
    records = out.split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record or len(record) < 4:
            continue
        status = record[:2]
        path = record[3:]
        if "R" in status or "C" in status:
            index += 1  # 跳过 rename/copy 的源路径
        paths.add(path.strip())
    return paths


PATH_TOKEN_RE = re.compile(r"`([^`\n]+)`")


def normalize_path_token(token: str) -> str | None:
    text = _unquote(_strip_comment(token.strip()))
    text = text.strip("`")
    text = _unquote(text.strip())
    text = text.strip("。，,；;：:`'\"")
    while text.startswith("./"):
        text = text[2:]
    if not text or " " in text or "\t" in text:
        return None
    if re.match(r"^(https?://|git |make |python3? |xcrun |xcodebuild )", text):
        return None
    if text.startswith(("-", "#", "|", ">")):
        return None
    if re.fullmatch(r"[0-9a-f]{7,40}", text):  # commit 短 hash
        return None
    if "/" in text or re.search(r"\.[A-Za-z0-9]{1,10}$", text):
        return text
    if text in {"Makefile", "Dockerfile", "LICENSE", "NOTICE"}:
        return text
    return None


def extract_paths(body: str) -> set[str]:
    """从“未提交改动”正文提取文件/目录：优先反引号路径，其次 `- 路径 / 意图` 行。"""
    found: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        for match in PATH_TOKEN_RE.finditer(stripped):
            token = normalize_path_token(match.group(1))
            if token:
                found.add(token)
        if stripped.startswith(("- ", "* ")):
            first = re.split(r"\s+/\s+", stripped[2:], maxsplit=1)[0].strip().rstrip("：:")
            token = normalize_path_token(first)
            if token:
                found.add(token)
    return found


def path_covered(paths: set[str], target: str) -> bool:
    for declared in paths:
        if declared == target:
            return True
        base = declared.rstrip("/")
        if target.startswith(base + "/"):
            return True
    return False


def in_allow(path: str, allow: list[str]) -> bool:
    if not allow:
        return True
    for pattern in allow:
        pat = str(pattern).strip()
        if not pat:
            continue
        if any(char in pat for char in "*?["):
            if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path, pat.rstrip("/") + "/*"):
                return True
            continue
        base = pat.rstrip("/")
        if path == base or path.startswith(base + "/"):
            return True
    return False


CLEAN_RE = re.compile(r"无未提交改动|没有未提交|工作区\s*(clean|干净)|全部已提交|已全部提交")


@dataclass
class UncommittedDiff:
    mismatches: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def diff_uncommitted(plan: Plan, active_only: bool = True) -> UncommittedDiff:
    """把计划“未提交改动”与 `git status` 交叉比对；不一致返回 mismatches。"""
    diff = UncommittedDiff()
    if active_only and plan.status != "active":
        diff.notes.append("非 active 计划，跳过未提交核对（done/archived 允许为空）")
        return diff
    sec = plan.section("未提交改动")
    if sec is None:
        diff.notes.append("计划缺少“未提交改动”节，无法与 git status 交叉比对")
        return diff
    content = section_text(plan, sec)
    if not content:
        diff.notes.append("“未提交改动”节为空，无法与 git status 交叉比对（无改动请写“无”）")
        return diff
    actual = git_status_paths()
    if actual is None:
        diff.notes.append("git 不可用，无法交叉比对未提交改动")
        return diff
    declared = extract_paths(content)
    clean_marker = bool(CLEAN_RE.search(content))
    if not declared and not clean_marker:
        diff.notes.append("无法从“未提交改动”节解析出文件路径（请写反引号路径或“- 路径 / 意图 / 可丢弃”）")
        return diff
    allow = meta_list(plan.meta, "scope.allow")
    scoped_actual = sorted(path for path in actual if in_allow(path, allow))
    # scope.allow 之外的改动必须报错，而不是被静默过滤（防止越界假绿）。
    for outside in sorted(path for path in actual if not in_allow(path, allow)):
        diff.mismatches.append(f"git 有 scope 外未提交改动（不在 allow）：{outside}")
    for declared_path in sorted(declared):
        base = declared_path.rstrip("/")
        if declared_path.endswith("/"):
            ok = any(path.startswith(declared_path) for path in scoped_actual)
        else:
            ok = path_covered(set(scoped_actual), declared_path)
        if not ok:
            diff.mismatches.append(f"计划声明未提交但 git 无改动：{declared_path}")
    for actual_path in scoped_actual:
        if not path_covered(declared, actual_path):
            diff.mismatches.append(f"git 有未提交改动但计划未声明：{actual_path}")
    if clean_marker and not declared and scoped_actual:
        diff.mismatches.append(
            f"计划声明无未提交改动，但 git 在 scope 内有 {len(scoped_actual)} 个改动（见 git status）"
        )
    return diff


# ---------------------------------------------------------------------------
# 验证证据表
# ---------------------------------------------------------------------------

def _is_separator(cells: list[str]) -> bool:
    stripped = [cell.replace(" ", "") for cell in cells if cell.strip()]
    return bool(stripped) and all(re.fullmatch(r":?-{2,}:?", cell) for cell in stripped)


def split_table_row(line: str) -> list[str]:
    """拆分 markdown 表格行：转义的 `\\|` 不当作列分隔（命令里的管道符常见）。"""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", text)]


def evidence_table(plan: Plan, sec: Section) -> tuple[list[str] | None, list[list[str]]]:
    """返回 (表头单元格, 数据行)；表头/数据行都没有时返回 (None, [])。"""
    lines = section_raw_lines(plan, sec)
    header: list[str] | None = None
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = split_table_row(stripped)
            if header is None:
                header = cells
                continue
            if _is_separator(cells):
                continue
            rows.append(cells)
        elif header is not None:
            break
    return header, rows


def evidence_status(plan: Plan) -> tuple[str, list[str]]:
    """返回 ("ok"|"missing"|"no-rows"|"bad-columns", 缺列说明)。"""
    sec = plan.section("验证证据")
    if sec is None:
        return "missing", []
    header, rows = evidence_table(plan, sec)
    if not header or not rows:
        return "no-rows", []
    missing = [name for name in EVIDENCE_COLS if not any(name in cell for cell in header)]
    if missing:
        return "bad-columns", missing
    return "ok", []


# ---------------------------------------------------------------------------
# 命令：new / latest / brief
# ---------------------------------------------------------------------------

def slugify(topic: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", topic.strip().lower()).strip("-")
    return slug


def cmd_new(topic: str) -> int:
    if not TEMPLATE.is_file():
        sys.exit(f"[FAIL] 缺少模板：{rel(TEMPLATE)}")
    slug = slugify(topic)
    if not slug:
        sys.exit("[FAIL] TOPIC 需包含字母、数字或汉字")
    today = dt.date.today().isoformat()
    path = PLANS / f"{today}-{slug}.md"
    if path.exists():
        sys.exit(f"[FAIL] 已存在：{rel(path)}")
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("<date>-<topic>", f"{today}-{slug}")
    text = text.replace("<主题>", topic.strip())
    text = text.replace("status: <active|done|blocked|archived>", "status: active")
    text = text.replace("updated: <YYYY-MM-DD>", f"updated: {today}")
    PLANS.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"已创建 {rel(path)}；填完目标/验收/下一步/scope 后开工（plan.py check 会机检）。")
    return 0


def cmd_latest(only_active: bool) -> int:
    plans = load_plans()
    if not plans:
        sys.exit("[FAIL] 没有计划文件；先运行：make plan TOPIC=<topic>")
    active = active_plans(plans)
    if only_active:
        if active:
            if len(active) > 1:
                print(f"[WARN] 有 {len(active)} 个 active 计划，按 updated/mtime 取最新", file=sys.stderr)
            print(rel(max(active, key=Plan.sort_key).path))
            return 0
        legacy = [plan for plan in plans if plan.legacy]
        if legacy:
            chosen = max(legacy, key=lambda p: p.sort_key())
            print("[WARN] 没有带 status 的 active 计划；legacy 计划按 mtime 兜底（建议补 front matter）", file=sys.stderr)
            print(rel(chosen.path))
            return 0
        sys.exit("[FAIL] 没有 status=active 的计划；用 `plan.py brief <path>` 查看历史计划。")
    if active:
        if len(active) > 1:
            print(f"[WARN] 有 {len(active)} 个 active 计划，按 updated/mtime 取最新", file=sys.stderr)
        print(rel(max(active, key=Plan.sort_key).path))
        return 0
    chosen = max(plans, key=lambda p: p.sort_key())
    if chosen.legacy:
        print("[WARN] 无 active 计划；选中计划是 legacy（无 front matter），按 mtime 兜底", file=sys.stderr)
    else:
        print(f"[WARN] 无 active 计划；回退到最新历史计划（status={chosen.status or 'legacy'}）", file=sys.stderr)
    print(rel(chosen.path))
    return 0


BRIEF_SECTIONS = (
    ("目标与非目标", ("目标与非目标", "目标与验收", "目标")),
    ("验收", ("验收",)),
    ("关键决策与理由", ("关键决策与理由", "关键决策", "设计原则", "结论摘要", "TL;DR")),
    ("进度", ("进度",)),
    ("已排除（勿重试）", ("已排除",)),
    ("验证证据", ("验证证据",)),
    ("未验证项", ("未验证项", "未运行 / 未验证", "未验证")),
    ("未提交改动", ("未提交改动",)),
    ("下一步", ("下一步",)),
    ("待确认", ("待确认",)),
)

REQUIRED_BRIEF = ("目标与非目标", "验收", "验证证据", "下一步")


def _print_plan_header(plan: Plan) -> None:
    status = plan.status or ("legacy" if plan.legacy else "缺少")
    bits = [f"status={status}"]
    for key in ("level", "owner", "updated"):
        value = plan.meta.get(key)
        if value:
            bits.append(f"{key}={value}")
    print(f"计划：{rel(plan.path)} | " + " | ".join(bits))
    if plan.legacy:
        print("[WARN] 该计划无 YAML front matter（legacy 模式，按 mtime 兜底）；建议补 id/status/scope。")


def cmd_brief(arg: str | None = None) -> int:
    plan = resolve_plan_arg(arg)
    print(f"按 AGENTS.md 接手；先读 {rel(plan.path)}，再继续。")
    _print_plan_header(plan)
    print()
    missing: list[str] = []
    for label, keywords in BRIEF_SECTIONS:
        sec = plan.section(*keywords)
        body = section_text(plan, sec)
        print(f"## {label}")
        if sec is None:
            print("（计划未单列此节）")
        elif not body:
            print("（本节为空或只有占位符）")
        elif label == "关键决策与理由" and sec.norm not in ("关键决策与理由", "关键决策"):
            print(f"（本计划未单列“关键决策”，以下回退自「{sec.title}」）")
            print(body)
        else:
            print(body)
        print()
        if label in REQUIRED_BRIEF and not body:
            missing.append(label)
    diff = diff_uncommitted(plan)
    for item in diff.mismatches:
        print(f"[WARN] {item}")
    for item in diff.notes:
        print(f"[INFO] {item}")
    if diff.mismatches or diff.notes:
        print()
    code, out, _ = git(["status", "--short"])
    print("git status --short:")
    print(out.rstrip() if code == 0 and out.strip() else "(clean)")
    print()
    for label in missing:
        print(f"[WARN] 计划缺少非空“{label}”，交接前补齐。")
    return 0


# ---------------------------------------------------------------------------
# 命令：check
# ---------------------------------------------------------------------------

def check_plan(plan: Plan) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if plan.legacy:
        warnings.append("无 front matter（legacy 计划，按 mtime 兜底；建议补 status）")
        return errors, warnings
    status = plan.status
    if not status:
        errors.append("缺少 front matter 字段 status")
    elif status not in VALID_STATUS:
        errors.append(f"status 非法：{status!r}（只允许 {'/'.join(VALID_STATUS)}）")
    plan_id = plan.meta.get("id")
    if not plan_id:
        warnings.append("front matter 缺少 id")
    elif str(plan_id) != plan.path.stem:
        warnings.append(f"id 与文件名不一致：id={plan_id}，文件名={plan.path.stem}")
    if not plan.meta.get("owner"):
        warnings.append("front matter 缺少 owner")
    level = str(plan.meta.get("level") or "")
    if level not in ("L0", "L1", "L2"):
        warnings.append(f"level 缺失或非法：{level!r}（应为 L0/L1/L2）")
    updated = str(plan.meta.get("updated") or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated):
        warnings.append(f"updated 缺失或格式非 YYYY-MM-DD：{updated!r}")
    if status in ("active", "done", "blocked"):
        for label, keywords in (("目标", ("目标与非目标", "目标与验收", "目标")),
                                ("验收", ("验收",)),
                                ("下一步", ("下一步",))):
            body = plan.section_text(*keywords)
            if not body and keywords == ("验收",):
                body = "\n".join(meta_list(plan.meta, "acceptance"))
            if not body:
                errors.append(f"{status} 计划缺少非空“{label}”")
        allow = meta_list(plan.meta, "scope.allow")
        if not allow:
            errors.append(f"{status} 计划缺少 scope.allow（允许改动的文件/目录）")
    evidence_strict = status in ("active", "done")
    state, detail = evidence_status(plan)
    if state == "missing":
        message = "缺少“验证证据”节（至少 1 行：命令/结果/环境/证据ID）"
        (errors if evidence_strict else warnings).append(message)
    elif state == "no-rows":
        message = "“验证证据”表缺失或没有数据行（需要 命令/结果/环境/证据ID）"
        (errors if evidence_strict else warnings).append(message)
    elif state == "bad-columns":
        message = f"“验证证据”表缺列：{'、'.join(detail)}（至少需要 命令/结果/环境）"
        (errors if evidence_strict else warnings).append(message)
    evidence_errors, evidence_warnings = evidence_audit(plan)
    errors.extend(evidence_errors)
    warnings.extend(evidence_warnings)
    if status == "active":
        diff = diff_uncommitted(plan)
        errors.extend(diff.mismatches)
        warnings.extend(diff.notes)
    return errors, warnings


EVIDENCE_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[a-z0-9][a-z0-9-]*$")
EVIDENCE_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
# 结果单元格里的“完成声明”词；命中时必须绑定可解析 evidence id 或白名单占位。
PASS_WORD_RE = re.compile(r"\bPASS\b|\bSUCCEEDED\b|通过|已验证|已完成")
# 动态测试声明（真机/模拟器/测试计数）：不允许仅靠“过程记录”旁注绕过 evidence id。
DYNAMIC_CLAIM_RE = re.compile(r"真机|device|DuiyiTests|DuiyiUITests|模拟器|xcresult|passed\s*=|skipped\s*=", re.I)
# 证据ID 占位白名单：命中即视为“非机器证据”的过程记录，允许不绑定 evidence id。
EVIDENCE_ANNOTATION_WORDS = ("基线", "过程", "外部", "历史", "未验证", "负向")
HARD_EVIDENCE_STATUSES = ("active", "done", "blocked")


def evidence_doc(evidence_id: str) -> tuple[str, dict | None]:
    """读取 harness/evidence/<id>.json：("ok", doc) / ("missing", None) / ("invalid", None)。"""
    path = ROOT / "harness" / "evidence" / f"{evidence_id}.json"
    if not path.is_file():
        return "missing", None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "invalid", None
    if not isinstance(doc, dict):
        return "invalid", None
    return "ok", doc


def _git_sha(rev: str) -> str | None:
    code, out, _ = git(["rev-parse", "--verify", f"{rev}^{{commit}}"])
    return out.strip() if code == 0 and out.strip() else None


def _git_is_ancestor(rev: str) -> bool:
    code, _, _ = git(["merge-base", "--is-ancestor", rev, "HEAD"])
    return code == 0


def submitted_tokens(plan: Plan) -> list[str]:
    """front matter `submitted` 的短 hash 列表（逗号/空格分隔；兼容字符串与内联列表）。"""
    raw = plan.meta.get("submitted")
    values: list[str] = []
    if isinstance(raw, list):
        values = [str(item) for item in raw]
    elif isinstance(raw, str):
        values = [raw]
    tokens: list[str] = []
    for value in values:
        for token in re.split(r"[,，\s]+", value.strip().strip("`")):
            token = token.strip().strip("`")
            if token:
                tokens.append(token)
    return tokens


def _submitted_errors(tokens: list[str]) -> list[str]:
    errors: list[str] = []
    for token in tokens:
        if not re.fullmatch(r"[0-9a-fA-F]{4,40}", token):
            errors.append(f"submitted 中的 commit 不是短 hash：{token!r}")
            continue
        if _git_sha(token) is None:
            errors.append(f"submitted 中的 commit 不存在：{token}")
            continue
        if not _git_is_ancestor(token):
            errors.append(f"submitted 中的 commit 不是 HEAD 或其祖先：{token}")
    return errors


def _commit_bound(commit: str, tokens: list[str]) -> bool:
    """证据 commit 等于 HEAD，或与 submitted 某个 token 前缀匹配。"""
    candidates: list[str] = []
    head = _git_sha("HEAD")
    if head:
        candidates.append(head)
    for token in tokens:
        sha = _git_sha(token)
        if sha:
            candidates.append(sha)
    for candidate in candidates:
        if candidate.startswith(commit) or commit.startswith(candidate):
            return True
    return False


def _result_excerpt(cell: str, limit: int = 60) -> str:
    text = re.sub(r"\s+", " ", cell.replace("**", "")).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def evidence_audit(plan: Plan) -> tuple[list[str], list[str]]:
    """验证证据硬校验（active/done/blocked 硬失败；archived 降级为 WARN）。

    1. 「验证证据」表头必须含「证据ID」列（含“证据”即可）；
    2. 可解析证据 ID 必须存在 harness/evidence/<id>.json 且 verdict=PASS；
    3. 结果含完成声明（PASS/通过/SUCCEEDED/已验证/已完成）时，证据ID 必须是可解析 id，
       或命中白名单占位（基线/过程/外部/历史/未验证/负向；空单元格 → ERROR）；
    4. active 无 PASS 证据 → WARN；done 无 PASS 证据 → ERROR；
    （5. 结构必填/证据节缺失由 check_plan 统一硬校验）
    6. done 必须有 submitted，且 token 可解析、是 HEAD 祖先；
    7. done 被引用证据的 git.commit 必须绑定 HEAD 或 submitted。
    """
    errors: list[str] = []
    warnings: list[str] = []
    if plan.legacy:
        return errors, warnings
    status = plan.status
    hard = status in HARD_EVIDENCE_STATUSES
    done_tokens: list[str] = []
    if status == "done":
        done_tokens = submitted_tokens(plan)
        if not done_tokens:
            errors.append("done 计划缺少 front matter submitted（提交短 hash，逗号/空格分隔）")
        else:
            errors.extend(_submitted_errors(done_tokens))
    sec = plan.section("验证证据")
    if sec is None:
        return errors, warnings
    header, rows = evidence_table(plan, sec)
    if not header or not rows:
        return errors, warnings
    id_index = next((index for index, cell in enumerate(header) if "证据" in cell), None)
    if id_index is None:
        message = (
            "“验证证据”表缺少「证据ID」列（表头需含“证据”；"
            "结果中的 PASS/通过/已完成 必须绑定 evidence id）"
        )
        (errors if hard else warnings).append(message)
        return errors, warnings
    result_index = next((index for index, cell in enumerate(header) if "结果" in cell), 1)
    pass_ids: list[str] = []
    referenced: dict[str, dict] = {}
    for row in rows:
        cells = list(row) + [""] * max(0, len(header) - len(row))
        evidence_cell = cells[id_index] if id_index < len(cells) else ""
        result_cell = cells[result_index] if result_index < len(cells) else ""
        evidence_id = evidence_cell.strip().strip("`").strip()
        if EVIDENCE_ID_RE.fullmatch(evidence_id):
            state, doc = evidence_doc(evidence_id)
            if state == "missing":
                message = f"证据 ID 不存在：{evidence_id}（harness/evidence/{evidence_id}.json 缺失）"
                (errors if hard else warnings).append(message)
                continue
            if state == "invalid" or doc is None:
                message = f"证据 JSON 无法解析：{evidence_id}"
                (errors if hard else warnings).append(message)
                continue
            referenced[evidence_id] = doc
            verdict = doc.get("verdict")
            if verdict == "PASS":
                pass_ids.append(evidence_id)
            else:
                message = f"证据 verdict 非 PASS：{evidence_id} = {verdict!r}"
                (errors if hard else warnings).append(message)
            continue
        if not PASS_WORD_RE.search(result_cell):
            continue
        annotated = any(word in evidence_cell for word in EVIDENCE_ANNOTATION_WORDS)
        if annotated and not DYNAMIC_CLAIM_RE.search(result_cell):
            continue
        if annotated and DYNAMIC_CLAIM_RE.search(result_cell):
            message = (
                f"结果声称动态测试完成（{_result_excerpt(result_cell)}）但用“过程记录”旁注绕过证据 ID："
                "真机/模拟器/测试计数类 claim 必须绑定 verdict=PASS 的 evidence id"
            )
            (errors if hard else warnings).append(message)
            continue
        if not evidence_id:
            message = (
                f"结果声称完成（{_result_excerpt(result_cell)}）但「证据ID」为空："
                "补 evidence id，或标注 —（过程记录：…）"
            )
        else:
            message = (
                f"结果声称完成（{_result_excerpt(result_cell)}）但证据 ID 不是可解析的 evidence id："
                f"{evidence_id}；补 evidence id，或标注 —（过程记录：…）"
            )
        (errors if hard else warnings).append(message)
    if status == "active" and not pass_ids:
        warnings.append("验证证据表中没有可解析且 verdict=PASS 的 evidence id（完成前补一条真实证据）")
    elif status == "done" and not pass_ids:
        errors.append("done 计划没有任何可解析且 verdict=PASS 的 evidence id（不能无证据收尾）")
    if status == "done":
        for evidence_id, doc in referenced.items():
            git_meta = doc.get("git")
            commit = ""
            if isinstance(git_meta, dict):
                commit = str(git_meta.get("commit") or "").strip().lower()
            if not commit:
                errors.append(f"证据缺 git.commit，无法绑定 submitted/HEAD：{evidence_id}")
            elif not EVIDENCE_COMMIT_RE.fullmatch(commit):
                errors.append(f"证据 git.commit 非法（应为 7–40 位短 hash）：{evidence_id} = {commit!r}")
            elif not _commit_bound(commit, done_tokens):
                errors.append(f"证据 commit 未绑定 submitted/HEAD：{evidence_id}（commit={commit}）")
    return errors, warnings


def run_check(verbose: bool = True) -> tuple[int, int]:
    plans = load_plans()
    if not plans:
        print(f"[FAIL] {rel(PLANS)} 下没有计划文件")
        return 1, 0
    active = active_plans(plans)
    if verbose:
        print(f"检查 {rel(PLANS)}/*.md（跳过 _template.md 与 _archive/）：")
    if len(active) > 1:
        names = "、".join(rel(plan.path) for plan in sorted(active, key=Plan.sort_key))
        print(f"[WARN] 有 {len(active)} 个 active 计划（协议：一次只做一个 active）：{names}")
    total_errors = 0
    total_warnings = 0
    for plan in plans:
        errors, warnings = check_plan(plan)
        tag = "FAIL" if errors else "OK"
        if verbose:
            print(f"[{tag}]  {rel(plan.path)}  status={plan.status or ('legacy' if plan.legacy else '缺失')}")
            for item in errors:
                print(f"       [FAIL] {item}")
            for item in warnings:
                print(f"       [WARN] {item}")
        total_errors += len(errors)
        total_warnings += len(warnings)
    return total_errors, total_warnings


def cmd_check() -> int:
    errors, warnings = run_check(verbose=True)
    verdict = "PASS" if errors == 0 else "FAIL"
    print(f"结论：{verdict}（{len(load_plans())} 个计划，{errors} error / {warnings} warn；WARN 不阻断门禁）")
    return 0 if errors == 0 else 1


# ---------------------------------------------------------------------------
# 命令：resume
# ---------------------------------------------------------------------------

def _first_item(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^(?:[-*]|\d+[.)])\s+(.*)$", stripped)
        return (match.group(1) if match else stripped).strip()
    return ""


def _progress_summary(plan: Plan) -> str:
    body = plan.section_text("进度")
    if not body:
        return "进度节为空"
    done: list[str] = []
    todo: list[str] = []
    for line in body.splitlines():
        match = re.match(r"^\s*[-*]\s+\[(x|X| )\]\s*(.+)$", line)
        if match:
            (done if match.group(1).lower() == "x" else todo).append(match.group(2).strip())
    parts: list[str] = []
    if done:
        parts.append(f"已完成 {len(done)} 项，最近：{done[-1]}")
    if todo:
        parts.append(f"待办 {len(todo)} 项，下一条：{todo[0]}")
    if parts:
        return "；".join(parts)
    return _first_item(body)[:120]


def _print_section(plan: Plan, label: str, keywords: tuple[str, ...]) -> None:
    body = plan.section_text(*keywords)
    print(f"## {label}")
    print(body if body else "（计划未单列此节）")
    print()


READING_LIST = (
    ("README.md + CONTRIBUTING.md", "项目入口、环境、签名、测试与坑"),
    ("docs/02-architecture.md", "数据链路与分层"),
    ("docs/04-roadmap.md", "问题清单与优先级（验收判据唯一源）"),
    ("references/verification.md", "验证矩阵 / 真机 / 性能口径"),
)


def cmd_resume() -> int:
    plan = require_active_plan()
    print("接手摘要（active 计划 + git 事实 + 下一步 1 条）")
    _print_plan_header(plan)
    next_body = plan.section_text("下一步")
    next_item = _first_item(next_body) or "（计划未写下一步）"
    print()
    print("三问速答：")
    who = plan.meta.get("id") or plan.path.stem
    print(f"- 我是谁：{who}（owner={plan.meta.get('owner') or '未知'} / {plan.meta.get('level') or '级别未知'} / status=active）")
    print(f"- 做到哪：{_progress_summary(plan)}")
    print(f"- 下一步：{next_item}")
    print()
    _print_section(plan, "目标与非目标", ("目标与非目标", "目标与验收", "目标"))
    _print_section(plan, "验收", ("验收",))
    key_sec = plan.section("关键决策与理由", "关键决策", "设计原则", "结论摘要", "TL;DR")
    if key_sec is not None:
        print(f"## 关键决策与理由（来自「{key_sec.title}」）")
        print(plan.section_text("关键决策与理由", "关键决策", "设计原则", "结论摘要", "TL;DR") or "（空）")
        print()
    _print_section(plan, "进度", ("进度",))
    _print_section(plan, "未验证项", ("未验证项", "未运行 / 未验证", "未验证"))
    diff = diff_uncommitted(plan)
    for item in diff.mismatches:
        print(f"[WARN] {item}")
    for item in diff.notes:
        print(f"[INFO] {item}")
    code, out, _ = git(["status", "--short"])
    print("git status --short:")
    print(out.rstrip() if code == 0 and out.strip() else "(clean)")
    print()
    code, out, _ = git(["log", "-5", "--oneline"])
    print("git log -5:")
    print(out.rstrip() if code == 0 and out.strip() else "(无提交历史或 git 不可用)")
    print()
    print("下一步（只做第 1 条）：")
    print(f"1. {next_item}")
    print()
    print("建议阅读：")
    for index, (path, why) in enumerate(READING_LIST, start=1):
        print(f"  {index}. {path} —— {why}")
    return 0


# ---------------------------------------------------------------------------
# 命令：end
# ---------------------------------------------------------------------------

def cmd_end() -> int:
    print("收尾检查（`make end` 已先跑 make verify-static；本命令只做计划/git 核对）")
    print()
    print("[1] 静态门禁提示：先跑 `make verify-static`（docs/架构/计数/harness/计划+脚本语法）")
    code, _, _ = git(["rev-parse", "--is-inside-work-tree"])
    if code == 0:
        print("    动态验证（测试/真机）不在本命令内；未跑就写“未验证”。")
    print()
    print("[2] 计划机检（等价 `python3 tools/plan.py check`）：")
    errors, warnings = run_check(verbose=True)
    print()
    plan = max(active_plans(load_plans()), key=Plan.sort_key, default=None)
    print("[3] git status --short:")
    _, out, _ = git(["status", "--short"])
    print(out.rstrip() if out.strip() else "(clean)")
    print()
    if plan is None:
        print("[WARN] 没有 active 计划；收尾核对跳过“未验证项/下一步”。")
    else:
        print(f"[4] 未验证项（来自 {rel(plan.path)}）：")
        unverified = plan.section_text("未验证项", "未运行 / 未验证", "未验证")
        print(unverified if unverified else "（计划未单列未验证项）")
        print()
        state, _ = evidence_status(plan)
        if state != "ok":
            print("[WARN] active 计划“验证证据”缺失或无效（需要 ≥1 行：命令/结果/环境）——完成前补可复核证据。")
            warnings += 1
        next_item = _first_item(plan.section_text("下一步")) or "（无）"
        print(f"[5] 下一步：{next_item}")
        print()
    print("[6] 提交前提醒：按团队规则先询问用户再提交；提交信息跟随仓库英文风格；不加 AI 署名；")
    print("    不提交 build/、harness/runs/、trace、他人签名信息；提交后把 short hash 回填 plan front matter。")
    print()
    verdict = "PASS" if errors == 0 else "FAIL"
    print(f"结论：{verdict}（{errors} error / {warnings} warn）")
    return 0 if errors == 0 else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    args = list(argv)
    if "--root" in args:
        index = args.index("--root")
        try:
            value = args[index + 1]
        except IndexError:
            sys.exit("用法：python3 tools/plan.py [--root <repo>] <命令>")
        set_root(value)
        del args[index: index + 2]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0 if args else 2
    command, rest = args[0], args[1:]
    if command == "new":
        if not rest:
            sys.exit("用法：python3 tools/plan.py new <topic>")
        return cmd_new(" ".join(rest))
    if command == "latest":
        unknown = [item for item in rest if item != "--active"]
        if unknown:
            sys.exit(f"用法：python3 tools/plan.py latest [--active]（未知参数：{' '.join(unknown)}）")
        return cmd_latest("--active" in rest)
    if command == "brief":
        if len(rest) > 1:
            sys.exit("用法：python3 tools/plan.py brief [计划路径]")
        return cmd_brief(rest[0] if rest else None)
    if command == "check":
        if rest:
            sys.exit("用法：python3 tools/plan.py check")
        return cmd_check()
    if command == "resume":
        if rest:
            sys.exit("用法：python3 tools/plan.py resume")
        return cmd_resume()
    if command == "end":
        if rest:
            sys.exit("用法：python3 tools/plan.py end")
        return cmd_end()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
