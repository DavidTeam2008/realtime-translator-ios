#!/usr/bin/env python3
"""harness-kit 通用计划校验器（标准库；无第三方依赖；不联网）。

用法（脚本被 init 复制到目标项目 tools/ 下）：
  python3 tools/check_plan.py [check] [--root PATH]
  python3 tools/check_plan.py new TOPIC [--root PATH]
  python3 tools/check_plan.py brief [PLAN_PATH] [--root PATH]

根目录 = 脚本上级目录（tools/ 的父目录）；--root 可覆盖。配置唯一来源
<root>/harness/config.json（缺失或字段不全 → 可读错误 + exit 1，不使用默认值）。

check 校验（FAIL 会计入退出码 1，WARN 不阻断）：
  - front matter 必填：id / status / level / owner / updated / scope.allow /
    acceptance / verify；status ∈ active|done|blocked|archived；updated 为
    YYYY-MM-DD；acceptance / verify / scope.allow 为非空列表。
  - 唯一 active：同时存在 >1 个 status=active 的计划 → FAIL（协议只允许一个
    活跃计划；否则 latest/resume 无法确定唯一目标）。本条在 docstring 固定。
  - status 为 active / done / blocked 时必填非空「目标（与非目标）」「验收」
    「下一步」节。
  - 「验证证据」节：Markdown 表头必须含 命令 / 结果 / 环境 / 证据ID 四列；
    证据 ID（形如 20260101T000000Z-name）必须存在于 <evidence>/<id>.json 且
    verdict=PASS；结果单元格声称 PASS/通过 时证据ID 必须是可解析 ID，或命中
    占位白名单（基线/过程/外部/历史/未验证/负向），否则 FAIL。
    active / done / blocked 硬校验；archived 降级为 WARN。
  - done：front matter `submitted` 必填（逗号/空格分隔短 hash），每个 token
    必须可解析且是 HEAD 祖先；被引用证据的 git.commit 必须等于 HEAD 或前缀
    匹配某个 submitted token。
  - active：「未提交改动」节与 `git status --short` 交叉比对；scope.allow 之外
    的改动、声明与真实改动不一致均 FAIL；缺该节时 WARN（无法核对）。
  - `new`：从 <plans>/_template.md 生成 <YYYY-MM-DD>-<topic>.md，并尽力替换
    常见占位符（<date>/<topic>/<主题>/{{DATE}}/{{TOPIC}}、status 占位）。
  - `brief`：打印 active 计划摘要；无 active 计划 → exit 1。

退出码：0 = 通过（允许 WARN）；1 = FAIL / 配置或计划不可用；2 = 用法错误。
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_REL = Path("harness") / "config.json"
VALID_STATUS = ("active", "done", "blocked", "archived")
STRICT_EVIDENCE_STATUS = ("active", "done", "blocked")
REQUIRED_FRONT = ("id", "status", "level", "owner", "updated", "acceptance", "verify")
EVIDENCE_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[a-z0-9-]+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
PASS_WORD_RE = re.compile(r"\bPASS\b|通过")
ANNOTATION_WORDS = ("基线", "过程", "外部", "历史", "未验证", "负向")
CLEAN_RE = re.compile(r"无未提交改动|没有未提交|工作区\s*(clean|干净)|全部已提交|已全部提交")
PATH_TOKEN_RE = re.compile(r"`([^`\n]+)`")


# ── 输出与 CLI ────────────────────────────────────────────────────────────
def fail(message: str, code: int = 1) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(code)


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def info(message: str) -> None:
    print(f"[INFO] {message}")


def parse_cli(argv: list[str]) -> tuple[Path, list[str]]:
    """解析全局 --root（可出现在任意位置），返回 (root, 其余参数)。"""
    args = list(argv)
    root: Path | None = None
    if "--root" in args:
        index = args.index("--root")
        if index + 1 >= len(args):
            fail("--root 需要一个目录参数", 2)
        root = Path(args[index + 1]).expanduser().resolve()
        del args[index:index + 2]
    if root is None:
        root = Path(__file__).resolve().parent.parent
    return root, args


# ── 配置 ─────────────────────────────────────────────────────────────────
def display(path: Path) -> str:
    return str(path)


def load_config(root: Path) -> dict:
    path = root / CONFIG_REL
    if not path.is_file():
        fail(f"缺少配置：{display(path)}（先运行 harness-init 生成 harness/config.json）")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"配置无法解析：{display(path)}：{exc}")
    if not isinstance(config, dict):
        fail(f"配置必须是 JSON object：{display(path)}")
    problems: list[str] = []
    for key in ("kitVersion", "project", "paths", "commands", "claims"):
        if key not in config:
            problems.append(f"缺少字段 {key}")
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    for key in ("docs", "references", "harness", "plans", "evidence", "tools"):
        if key not in paths:
            problems.append(f"缺少字段 paths.{key}")
    commands = config.get("commands") if isinstance(config.get("commands"), dict) else {}
    if not isinstance(commands.get("test"), str) or not commands.get("test", "").strip():
        problems.append("缺少字段 commands.test")
    claims = config.get("claims")
    if not isinstance(claims, list) or not claims:
        problems.append("缺少非空字段 claims")
    else:
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                problems.append(f"claims[{index}] 必须是 object")
                continue
            if not isinstance(claim.get("name"), str) or not claim.get("name"):
                problems.append(f"claims[{index}].name 缺失")
            if claim.get("type") not in ("test-count", "static"):
                problems.append(f"claims[{index}].type 必须是 test-count|static")
    for key, value in paths.items():
        if isinstance(value, list):  # 如 paths.rootDocs
            if not all(isinstance(item, str) and item for item in value):
                problems.append(f"paths.{key} 列表项必须是非空字符串")
            continue
        if not isinstance(value, str) or not value:
            problems.append(f"paths.{key} 必须是非空字符串或字符串列表")
            continue
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts:
            problems.append(f"paths.{key} 必须是仓库相对路径且不含 ..：{value!r}")
    if problems:
        fail("配置不可用：\n  - " + "\n  - ".join(problems))
    return config


def config_path(root: Path, config: dict, key: str) -> Path:
    return root / config["paths"][key]


def claim_names(config: dict) -> list[str]:
    return [
        claim.get("name", "")
        for claim in config.get("claims", [])
        if isinstance(claim, dict) and claim.get("name")
    ]


# ── git ──────────────────────────────────────────────────────────────────
def git(root: Path, args: list[str]) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover - 防御
        return 127, "", str(exc)


def git_is_repo(root: Path) -> bool:
    code, out, _ = git(root, ["rev-parse", "--is-inside-work-tree"])
    return code == 0 and out.strip() == "true"


def git_status_paths(root: Path) -> set[str] | None:
    code, out, _ = git(root, ["status", "--porcelain", "-z", "--untracked-files=all"])
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
        status, path = record[:2], record[3:]
        if "R" in status or "C" in status:
            index += 1
        paths.add(path.strip())
    return paths


def git_sha(root: Path, rev: str) -> str | None:
    code, out, _ = git(root, ["rev-parse", "--verify", f"{rev}^{{commit}}"])
    return out.strip() if code == 0 and out.strip() else None


def git_is_ancestor(root: Path, rev: str) -> bool:
    code, _, _ = git(root, ["merge-base", "--is-ancestor", rev, "HEAD"])
    return code == 0


# ── front matter 解析（极简 YAML 子集） ──────────────────────────────────
def split_front_matter(text: str) -> tuple[str | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1:])
    return None, text


def strip_comment(value: str) -> str:
    return re.sub(r"(?:^|\s+)#.*$", "", value).rstrip()


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1].strip()
    return value


def split_inline_list(value: str) -> list[str]:
    text = value.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return [unquote(text)] if text else []
    inner = text[1:-1].strip()
    return [unquote(item.strip()) for item in inner.split(",") if item.strip()] if inner else []


def parse_front_matter(block: str) -> dict:
    meta: dict = {}
    top: str | None = None
    current_list: str | None = None
    for raw in block.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if stripped.startswith("- "):
            item = unquote(strip_comment(stripped[2:].strip()))
            if current_list is not None:
                meta.setdefault(current_list, [])
                if isinstance(meta[current_list], list):
                    meta[current_list].append(item)
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$", stripped)
        if not match:
            current_list = None
            continue
        key, value = match.group(1), strip_comment(match.group(2)).strip()
        full = key if indent == 0 else (f"{top}.{key}" if top else key)
        if indent == 0:
            top = key
        if not value:
            meta[full] = []
            current_list = full
        elif value.startswith("[") and value.endswith("]"):
            meta[full] = split_inline_list(value)
            current_list = None
        else:
            meta[full] = unquote(value)
            current_list = None
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


# ── 正文分节 ─────────────────────────────────────────────────────────────
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def normalize_title(title: str) -> str:
    text = re.sub(r"^\d+(?:\.\d+)*[.、)]?\s*", "", title.strip())
    return re.sub(r"\s*[（(][^（）()]*[）)]\s*$", "", text).strip()


@dataclass
class Section:
    level: int
    title: str
    norm: str
    start: int
    end: int


def parse_sections(body: str) -> list[Section]:
    lines = body.splitlines()
    headings = [
        (index, len(match.group(1)), match.group(2).strip())
        for index, line in enumerate(lines)
        if (match := HEADING_RE.match(line))
    ]
    sections: list[Section] = []
    for pos, (start, level, title) in enumerate(headings):
        end = len(lines)
        for later in range(pos + 1, len(headings)):
            if headings[later][1] <= level:
                end = headings[later][0]
                break
        sections.append(Section(level, title, normalize_title(title), start, end))
    return sections


def find_section(sections: list[Section], keywords: tuple[str, ...]) -> Section | None:
    for keyword in keywords:
        needle = keyword.lower()
        for matcher in (
            lambda norm: norm == needle,
            lambda norm: norm.startswith(needle),
            lambda norm: needle in norm,
        ):
            for section in sections:
                if matcher(section.norm.lower()):
                    return section
    return None


def dedent(lines: list[str]) -> list[str]:
    indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
    if not indents:
        return lines
    cut = min(indents)
    return [line[cut:] if line.strip() else "" for line in lines]


def section_lines(plan: "Plan", section: Section) -> list[str]:
    return dedent(plan.body.splitlines()[section.start + 1: section.end])


PLACEHOLDER_LINES = {
    "",
    "-",
    "- [ ]",
    "- [x]",
    "1.",
    "1",
    "- 目标：",
    "- 非目标：",
    "- 验收：",
    "- 验收（可执行判据）：",
    "文件 / 意图 / 是否可丢弃：",
    "方案 / 失败原因 / 证据：",
    "- （待填）",
}


def is_placeholder_line(line: str) -> bool:
    text = line.strip()
    if text in PLACEHOLDER_LINES:
        return True
    return bool(re.fullmatch(r"<[^>]*>", text))


def section_text(plan: "Plan", section: Section | None) -> str:
    """原文（用于打印）。"""
    if section is None:
        return ""
    kept = [
        line.rstrip()
        for line in section_lines(plan, section)
        if line.strip() and line.strip() not in ("---", "***", "___")
    ]
    return "\n".join(kept).strip()


def section_meaningful(plan: "Plan", section: Section | None) -> str:
    """去掉占位行后的正文（用于“必填节非空”判断）。"""
    if section is None:
        return ""
    kept: list[str] = []
    for line in section_lines(plan, section):
        stripped = line.strip()
        if not stripped or stripped in ("---", "***", "___"):
            continue
        if re.fullmatch(r"<!--.*-->", stripped):
            continue
        if is_placeholder_line(stripped):
            continue
        kept.append(line.rstrip())
    return "\n".join(kept).strip()


def is_placeholder_value(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"\s*<[^>]*>\s*", value))


# ── 计划 ─────────────────────────────────────────────────────────────────
@dataclass
class Plan:
    path: Path
    text: str
    body: str
    meta: dict = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)
    has_front_matter: bool = False

    @property
    def status(self) -> str | None:
        value = self.meta.get("status")
        return value.strip().lower() if isinstance(value, str) and value.strip() else None

    def section(self, *keywords: str) -> Section | None:
        return find_section(self.sections, tuple(keywords))


def read_plan(path: Path) -> Plan:
    text = path.read_text(encoding="utf-8")
    block, body = split_front_matter(text)
    meta = parse_front_matter(block) if block is not None else {}
    return Plan(path=path, text=text, body=body, meta=meta,
                sections=parse_sections(body), has_front_matter=block is not None)


def plan_files(root: Path, config: dict) -> list[Path]:
    plans_dir = config_path(root, config, "plans")
    if not plans_dir.is_dir():
        fail(f"计划目录不存在：{display(plans_dir)}（先运行 harness-init 生成）")
    return sorted(path for path in plans_dir.glob("*.md") if path.name != "_template.md")


def load_plans(root: Path, config: dict) -> list[Plan]:
    return [read_plan(path) for path in plan_files(root, config)]


def plan_rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return display(path)


# ── 证据表 ───────────────────────────────────────────────────────────────
def split_table_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", text)]


def is_separator(cells: list[str]) -> bool:
    stripped = [cell.replace(" ", "") for cell in cells if cell.strip()]
    return bool(stripped) and all(re.fullmatch(r":?-{2,}:?", cell) for cell in stripped)


def evidence_table(plan: Plan, section: Section | None) -> tuple[list[str] | None, list[list[str]]]:
    if section is None:
        return None, []
    header: list[str] | None = None
    rows: list[list[str]] = []
    for line in section_lines(plan, section):
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = split_table_row(stripped)
            if header is None:
                header = cells
                continue
            if is_separator(cells):
                continue
            rows.append(cells)
        elif header is not None:
            break
    return header, rows


# ── 计划校验 ─────────────────────────────────────────────────────────────
def load_evidence_doc(root: Path, config: dict, evidence_id: str) -> tuple[str, dict | None]:
    path = config_path(root, config, "evidence") / f"{evidence_id}.json"
    if not path.is_file():
        return "missing", None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "invalid", None
    return ("ok", doc) if isinstance(doc, dict) else ("invalid", None)


def submitted_tokens(plan: Plan) -> list[str]:
    raw = plan.meta.get("submitted")
    values = [str(item) for item in raw] if isinstance(raw, list) else ([raw] if isinstance(raw, str) else [])
    tokens: list[str] = []
    for value in values:
        for token in re.split(r"[,，\s]+", value.strip().strip("`")):
            token = token.strip().strip("`")
            if token:
                tokens.append(token)
    return tokens


def commit_bound(root: Path, commit: str, tokens: list[str]) -> bool:
    candidates: list[str] = []
    head = git_sha(root, "HEAD")
    if head:
        candidates.append(head)
    for token in tokens:
        sha = git_sha(root, token)
        if sha:
            candidates.append(sha)
    return any(candidate.startswith(commit) or commit.startswith(candidate) for candidate in candidates)


def path_covered(declared: set[str], target: str) -> bool:
    for item in declared:
        base = item.rstrip("/")
        if item.endswith("/") and target.startswith(item):
            return True
        if target == item or (base and target.startswith(base + "/")):
            return True
    return False


def in_allow(path: str, allow: list[str]) -> bool:
    for pattern in allow:
        text = str(pattern).strip()
        if not text:
            continue
        base = text.rstrip("/")
        if any(char in text for char in "*?["):
            if fnmatch.fnmatch(path, text) or fnmatch.fnmatch(path, base + "/*"):
                return True
            continue
        if path == base or (base and path.startswith(base + "/")):
            return True
    return False


def normalize_path_token(token: str) -> str | None:
    text = unquote(strip_comment(token.strip())).strip("`").strip()
    text = text.strip("。，,；;：:`'\"")
    while text.startswith("./"):
        text = text[2:]
    if not text or " " in text or text.startswith(("-", "#", "|", ">")):
        return None
    if re.match(r"^(https?://|git |make |python3? )", text):
        return None
    if re.fullmatch(r"[0-9a-f]{7,40}", text):
        return None
    if "/" in text or re.search(r"\.[A-Za-z0-9]{1,10}$", text):
        return text
    return None


def declared_paths(content: str) -> set[str]:
    found: set[str] = set()
    for line in content.splitlines():
        stripped = line.strip()
        for match in PATH_TOKEN_RE.finditer(stripped):
            token = normalize_path_token(match.group(1))
            if token:
                found.add(token)
        if stripped.startswith(("- ", "* ")):
            token = normalize_path_token(re.split(r"\s+/\s+", stripped[2:], maxsplit=1)[0].strip().rstrip("：:"))
            if token:
                found.add(token)
    return found


def check_uncommitted(plan: Plan, root: Path, config: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    section = plan.section("未提交改动")
    content = section_text(plan, section)
    if section is None or not content:
        warnings.append("缺少「未提交改动」节，无法与 git status --short 交叉比对")
        return errors, warnings
    actual = git_status_paths(root)
    if actual is None:
        warnings.append("git 不可用或不是 git 仓库，无法交叉比对未提交改动")
        return errors, warnings
    allow = meta_list(plan.meta, "scope.allow")
    for outside in sorted(path for path in actual if not in_allow(path, allow)):
        errors.append(f"git 有 scope.allow 之外的未提交改动：{outside}")
    scoped = sorted(path for path in actual if in_allow(path, allow))
    declared = declared_paths(content)
    clean = bool(CLEAN_RE.search(content))
    for item in sorted(declared):
        covered = any(path.startswith(item) for path in scoped) if item.endswith("/") else path_covered(set(scoped), item)
        if not covered:
            errors.append(f"计划声明未提交但 git 无改动：{item}")
    for path in scoped:
        if not path_covered(declared, path):
            errors.append(f"git 有未提交改动但计划未声明：{path}")
    if clean and not declared and scoped:
        errors.append(f"计划声明无未提交改动，但 git 在 scope.allow 内有 {len(scoped)} 个改动")
    return errors, warnings


def check_evidence(plan: Plan, root: Path, config: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    status = plan.status
    hard = status in STRICT_EVIDENCE_STATUS
    done_tokens: list[str] = []
    if status == "done":
        done_tokens = submitted_tokens(plan)
        if not done_tokens:
            errors.append("done 计划缺少 front matter submitted（提交短 hash，逗号/空格分隔）")
        else:
            sha_ok = git_is_repo(root)
            for token in done_tokens:
                if not re.fullmatch(r"[0-9a-fA-F]{4,40}", token):
                    errors.append(f"submitted 中的 commit 不是短 hash：{token!r}")
                    continue
                if not sha_ok or git_sha(root, token) is None:
                    errors.append(f"submitted 中的 commit 不存在：{token}")
                    continue
                if not git_is_ancestor(root, token):
                    errors.append(f"submitted 中的 commit 不是 HEAD 或其祖先：{token}")
    section = plan.section("验证证据")
    header, rows = evidence_table(plan, section)
    issue = errors if hard else warnings
    if section is None:
        issue.append("缺少「验证证据」节（至少 1 行：命令/结果/环境/证据ID）")
        return errors, warnings
    if not header or not rows:
        issue.append("「验证证据」表缺失或没有数据行（需要 命令/结果/环境/证据ID 四列）")
        return errors, warnings
    missing_columns = [name for name in ("命令", "结果", "环境") if not any(name in cell for cell in header)]
    if not any("证据" in cell for cell in header):
        missing_columns.append("证据ID")
    if missing_columns:
        issue.append(f"「验证证据」表缺列：{'、'.join(missing_columns)}（需要 命令/结果/环境/证据ID）")
        return errors, warnings
    evidence_index = next(index for index, cell in enumerate(header) if "证据" in cell)
    result_index = next((index for index, cell in enumerate(header) if "结果" in cell), 1)
    referenced: dict[str, dict] = {}
    pass_ids = 0
    for row in rows:
        cells = list(row) + [""] * max(0, len(header) - len(row))
        evidence_cell = cells[evidence_index] if evidence_index < len(cells) else ""
        result_cell = cells[result_index] if result_index < len(cells) else ""
        evidence_id = evidence_cell.strip().strip("`").strip()
        if EVIDENCE_ID_RE.fullmatch(evidence_id):
            state, doc = load_evidence_doc(root, config, evidence_id)
            if state == "missing":
                issue.append(f"证据 ID 不存在：{evidence_id}（{config['paths']['evidence']}/{evidence_id}.json 缺失）")
                continue
            if state == "invalid" or doc is None:
                issue.append(f"证据 JSON 无法解析：{evidence_id}")
                continue
            referenced[evidence_id] = doc
            if doc.get("verdict") == "PASS":
                pass_ids += 1
            else:
                issue.append(f"证据 verdict 非 PASS：{evidence_id} = {doc.get('verdict')!r}")
            continue
        if not PASS_WORD_RE.search(result_cell):
            continue
        if any(word in evidence_cell for word in ANNOTATION_WORDS):
            continue
        excerpt = re.sub(r"\s+", " ", result_cell.replace("**", "")).strip()[:60]
        if not evidence_id:
            issue.append(f"结果声称完成（{excerpt}）但「证据ID」为空：补 evidence id，或标注 —（过程记录：…）")
        else:
            issue.append(
                f"结果声称完成（{excerpt}）但证据 ID 不是可解析的 evidence id：{evidence_id}"
                "；补 evidence id，或标注 —（过程记录：…）"
            )
    if status == "active" and pass_ids == 0:
        warnings.append("验证证据表中没有可解析且 verdict=PASS 的 evidence id（完成前补一条真实证据）")
    if status == "done":
        if pass_ids == 0:
            errors.append("done 计划没有任何可解析且 verdict=PASS 的 evidence id（不能无证据收尾）")
        for evidence_id, doc in referenced.items():
            git_meta = doc.get("git")
            commit = str(git_meta.get("commit") or "").strip().lower() if isinstance(git_meta, dict) else ""
            if not commit:
                errors.append(f"证据缺 git.commit，无法绑定 submitted/HEAD：{evidence_id}")
            elif not COMMIT_RE.fullmatch(commit):
                errors.append(f"证据 git.commit 非法（应为 7–40 位短 hash）：{evidence_id} = {commit!r}")
            elif not commit_bound(root, commit, done_tokens):
                errors.append(f"证据 commit 未绑定 submitted/HEAD：{evidence_id}（commit={commit}）")
    return errors, warnings


def check_plan(plan: Plan, root: Path, config: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not plan.has_front_matter:
        errors.append("缺少 front matter（需要 --- ... --- 块，含 id/status/level/owner/updated/scope.allow/acceptance/verify）")
        return errors, warnings
    for name in REQUIRED_FRONT:
        value = plan.meta.get(name)
        if name in ("acceptance", "verify"):
            items = [item for item in meta_list(plan.meta, name) if not is_placeholder_value(item)]
            if not items:
                errors.append(f"front matter 缺少非空 {name} 列表")
        elif not isinstance(value, str) or not value.strip() or is_placeholder_value(value):
            errors.append(f"front matter 缺少字段 {name}")
    allow = [item for item in meta_list(plan.meta, "scope.allow") if not is_placeholder_value(item)]
    if not allow:
        errors.append("front matter 缺少非空 scope.allow（允许改动的文件/目录）")
    status = plan.status
    if status not in VALID_STATUS:
        errors.append(f"status 非法：{plan.meta.get('status')!r}（只允许 {'/'.join(VALID_STATUS)}）")
    updated = plan.meta.get("updated")
    if isinstance(updated, str) and updated.strip() and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated.strip()):
        errors.append(f"front matter updated 需为 YYYY-MM-DD：{updated!r}")
    plan_id = plan.meta.get("id")
    if isinstance(plan_id, str) and plan_id.strip() and plan_id.strip() != plan.path.stem:
        warnings.append(f"front matter id 与文件名不一致：id={plan_id}，文件名={plan.path.stem}")
    if status in STRICT_EVIDENCE_STATUS:
        for label, keywords in (("目标", ("目标与非目标", "目标与验收", "目标")),
                                ("验收", ("验收",)),
                                ("下一步", ("下一步",))):
            if not section_meaningful(plan, plan.section(*keywords)):
                errors.append(f"{status} 计划缺少非空「{label}」节")
    evidence_errors, evidence_warnings = check_evidence(plan, root, config)
    errors.extend(evidence_errors)
    warnings.extend(evidence_warnings)
    if status == "active":
        uncommitted_errors, uncommitted_warnings = check_uncommitted(plan, root, config)
        errors.extend(uncommitted_errors)
        warnings.extend(uncommitted_warnings)
    return errors, warnings


def run_check(root: Path, config: dict) -> int:
    plans = load_plans(root, config)
    print(f"检查 {plan_rel(root, config_path(root, config, 'plans'))}/*.md（跳过 _template.md）：")
    if not plans:
        info("没有计划文件（新项目可先运行 check_plan.py new TOPIC）")
        print("结论：PASS（0 个计划）")
        return 0
    active = [plan for plan in plans if plan.status == "active"]
    errors_total = 0
    warnings_total = 0
    for plan in plans:
        errors, warnings = check_plan(plan, root, config)
        tag = "FAIL" if errors else "OK"
        print(f"[{tag}]  {plan_rel(root, plan.path)}  status={plan.status or '缺失'}")
        for item in errors:
            print(f"       [FAIL] {item}")
        for item in warnings:
            print(f"       [WARN] {item}")
        errors_total += len(errors)
        warnings_total += len(warnings)
    if len(active) > 1:
        names = "、".join(plan_rel(root, plan.path) for plan in active)
        print(f"[FAIL] 同时存在 {len(active)} 个 active 计划（只允许 1 个）：{names}")
        errors_total += 1
    verdict = "PASS" if errors_total == 0 else "FAIL"
    print(f"结论：{verdict}（{len(plans)} 个计划，{errors_total} error / {warnings_total} warn）")
    return 0 if errors_total == 0 else 1


# ── new / brief ──────────────────────────────────────────────────────────
def slugify(topic: str) -> str:
    return re.sub(r"[^\w.-]+", "-", topic.strip().lower()).strip("-")


def cmd_new(root: Path, config: dict, topic: str) -> int:
    template = config_path(root, config, "plans") / "_template.md"
    if not template.is_file():
        fail(f"缺少计划模板：{display(template)}（先运行 harness-init 生成）")
    slug = slugify(topic)
    if not slug:
        fail("TOPIC 需包含字母、数字或其它可见字符")
    today = dt.date.today().isoformat()
    target = config_path(root, config, "plans") / f"{today}-{slug}.md"
    if target.exists():
        fail(f"计划已存在：{display(target)}")
    text = template.read_text(encoding="utf-8")
    for token in ("{{DATE}}", "<date>", "<DATE>"):
        text = text.replace(token, today)
    for token in ("{{TOPIC}}", "<topic>", "<TOPIC>"):
        text = text.replace(token, topic.strip())
    text = text.replace("<主题>", topic.strip())
    # 尽力把 front matter 占位替换为可机检值（模板字段缺失时保持原样）。
    text = re.sub(r"(?m)^status:\s*<[^>\n]*>", "status: active", text)
    text = re.sub(r"(?m)^updated:\s*<[^>\n]*>", f"updated: {today}", text)
    text = re.sub(r"(?m)^id:\s*<[^>\n]*>", f"id: {today}-{slug}", text)
    target.write_text(text, encoding="utf-8")
    print(f"[OK] 已创建 {plan_rel(root, target)}；填完目标/验收/下一步/scope 后开工（check 会机检）。")
    return 0


BRIEF_SECTIONS = (
    ("目标与非目标", ("目标与非目标", "目标与验收", "目标")),
    ("验收", ("验收",)),
    ("进度", ("进度",)),
    ("已排除", ("已排除",)),
    ("验证证据", ("验证证据",)),
    ("未验证项", ("未验证项", "未验证")),
    ("未提交改动", ("未提交改动",)),
    ("下一步", ("下一步",)),
    ("待确认", ("待确认",)),
)


def cmd_brief(root: Path, config: dict, path_arg: str | None) -> int:
    if path_arg:
        path = Path(path_arg)
        if not path.is_absolute():
            path = root / path
        if not path.is_file():
            fail(f"计划不存在：{path_arg}")
        plan = read_plan(path)
    else:
        plans = [item for item in load_plans(root, config) if item.status == "active"]
        if not plans:
            fail("没有 active 计划（status: active）；用 check_plan.py new TOPIC 新建")
        plan = max(plans, key=lambda item: item.path.name)
    print(f"按计划接手；先读 {plan_rel(root, plan.path)}，再继续。")
    print(f"计划：{plan_rel(root, plan.path)} | status={plan.status or '缺失'}")
    print()
    for label, keywords in BRIEF_SECTIONS:
        body = section_text(plan, plan.section(*keywords))
        print(f"## {label}")
        print(body if body else "（计划未单列此节）")
        print()
    return 0


# ── main ─────────────────────────────────────────────────────────────────
def main(argv: list[str]) -> int:
    root, args = parse_cli(argv)
    if args and args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    config = load_config(root)
    command = args[0] if args else "check"
    rest = args[1:]
    if command == "check":
        if rest:
            fail(f"用法：check_plan.py [check] [--root PATH]（未知参数：{' '.join(rest)}）", 2)
        return run_check(root, config)
    if command == "new":
        if not rest:
            fail("用法：check_plan.py new TOPIC", 2)
        return cmd_new(root, config, " ".join(rest))
    if command == "brief":
        if len(rest) > 1:
            fail("用法：check_plan.py brief [PLAN_PATH]", 2)
        return cmd_brief(root, config, rest[0] if rest else None)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
