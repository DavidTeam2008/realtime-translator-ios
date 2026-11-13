#!/usr/bin/env python3
"""harness-kit 通用证据三值判定（标准库；无第三方依赖；不联网）。

用法（脚本被 init 复制到目标项目 tools/ 下）：
  python3 tools/verify_claim.py --all [--fresh] [--strict] [--allow-untracked] [--root PATH]

根目录 = 脚本上级目录（tools/ 的父目录）；--root 可覆盖。配置唯一来源
<root>/harness/config.json；证据在 config.paths.evidence 下（递归扫描，路径含
`_archive` 段的是归档证据），claim 定义见 config.claims（type=test-count|static）。

每个当前证据输出固定一行：
  CLAIM <evidence-id>: PASS|FAIL|UNVERIFIED — <原因>
归档证据逐个输出（不参与三值聚合、不改变退出码）：
  CLAIM <evidence-id>: SUPERSEDED — <取代关系或“未声明取代关系”>

判定规则：
  - 证据 verdict=FAIL → FAIL；verdict=UNVERIFIED → UNVERIFIED；verdict 非法 → FAIL。
  - 当前证据必须被 git 跟踪（`git ls-files --error-unmatch`）；非 git 仓库全局 WARN
    一次后跳过。未跟踪且最终 PASS → UNVERIFIED（CI 无法复核）；已是 FAIL/UNVERIFIED
    则保留并追加说明；`--allow-untracked` 不降级，只输出 WARN（显式逃生口）。
    `--strict` 下 `--allow-untracked` 无效（仍强制 UNVERIFIED）。
  - 当前证据 `result.artifacts`（及 legacy xcresultPath）里的每个 artifact 也必须被
    git 跟踪且存在；未跟踪/不存在 → UNVERIFIED（`--allow-untracked` 只 WARN，`--strict`
    强制 UNVERIFIED）。宁可误严，不能本地 PASS、CI 不可复核。
  - 必需 claim 完整性：config.claims 每项 `required` 默认 true；某个 required claim 没有
    claim 匹配的当前证据 → 输出 `CLAIM <claim>: UNVERIFIED — 缺少当前证据`，参与 exit 2；
    `required: false` 可显式 opt-out（避免删掉 tests-pass 只剩 docs-pass 仍 PASS）。
  - 归档 FAIL/UNVERIFIED 不得静默：必须有 claim 相同、存在且非自环的当前 PASS 证据在
    `supersedes` 中声明接管该 id；否则输出
    `CLAIM <archived-id>: UNVERIFIED — 归档失败/未验证证据未被合法取代` 并至少 UNVERIFIED。
    归档 PASS（或无法解析的归档）只列 SUPERSEDED，不惩罚。
  - verdict=PASS 时按 claim 类型复核：
    * 环境声明（claim.environment，可选 {id, requires[], os, python}）必须先匹配：
      证据 environment 缺 id / id 不等 / requires 未覆盖 / os、python 不匹配 →
      UNVERIFIED（在计数校验前判定，原因列出差集）。`os` 用词段匹配（linux 匹配
      linux-gnu / gnu/linux），`python` 用版本边界匹配（3.12 匹配 3.12.x，不匹配 3.120）。
      `claim.floorByEnvironment`（env→int）可按证据 environment.id 选择 floor；缺 id /
      未定义 → UNVERIFIED。配置非法仍 FAIL。
    * test-count：读 claim.baseline + claim.floor / claim.expectedSkipped。
      expectedSkipped 支持：字符串点号路径（baseline 值为 int / {min,max} /
      {byEnvironment}），或 claim 内直接写 object（min/max、byEnvironment）；
      区间为闭区间；byEnvironment 需要证据 environment.id（缺 id 或未定义 → UNVERIFIED）；
      非法配置 → FAIL。区间宽度 `max-min` 不得超过 `config.harden.maxSkippedRange`
      （默认 5），byEnvironment 分支同样适用；超过 → FAIL 并提示收紧。
      provenance：git.commit 必须可解析且是 HEAD 或其祖先，git.dirty 必须为 false。
      artifact：result.artifacts（数组；result.xcresultPath 为 legacy 兼容）必须存在；
      claim.requireArtifact 缺省为 **true**（显式 false 仅用于 legacy opt-out）；
      有 JUnit XML artifact 时从 XML 独立重算 passed/failed/skipped，与自报值不一致 → FAIL；
      无 artifact 或只有非 XML artifact（xcresult 等）→ UNVERIFIED（无法独立重算）。
      再要求 failed==0、passed>=floor、skipped 命中 expectedSkipped。
    * static：复跑 claim.command；exit 0 → PASS，非 0 → FAIL，command 缺失 → UNVERIFIED。
      static claim 每次重跑命令，freshness 不适用：`--fresh` 下不做 STALE 判定，原因注明。
  - --fresh 按 config.freshness[claim] 的 glob 比较 evidence.git.commit 与当前工作树
    （含已提交增量、未提交与未跟踪文件；过程目录 evidence/plans/reviews 不计）；
    有相关变更即 STALE。--strict 隐含 --fresh，且 STALE 的 PASS 降级为 UNVERIFIED；
    不加 --strict 时保留 PASS 并在原因里标注 STALE。
  - 只有归档证据、没有当前证据 → `CLAIM <none>: UNVERIFIED`，exit 2（归档不能让聚合变绿）。
  - 没有证据文件 → 输出 UNVERIFIED 语义（exit 2），避免“空证据”被当全绿。

聚合退出码（只统计当前证据）：任一 FAIL → 1；否则任一 UNVERIFIED → 2；全 PASS → 0。
用法错误 → 2（与 UNVERIFIED 同码，调用方按输出区分）。

约定：只扫描文件名形如 `<UTC>-<claim>.json` 的证据文件；`TEMPLATE.json` 等跳过。
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CONFIG_REL = Path("harness") / "config.json"
EVIDENCE_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[a-z0-9-]+$")
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")
COMMAND_TIMEOUT = 600
ARCHIVE_DIRNAME = "_archive"
UNTRACKED_NOTE = "证据文件未被 git 跟踪（CI 无法复核）"


# ── 输出与 CLI ────────────────────────────────────────────────────────────
def fail(message: str, code: int = 1) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(code)


def display(path: Path) -> str:
    return str(path)


def parse_cli(argv: list[str]) -> tuple[Path, list[str]]:
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


def git_tracked(root: Path, rel: str) -> bool:
    """当前证据文件必须被 git 跟踪：`git ls-files --error-unmatch -- <rel>`。"""
    code, _, _ = git(root, ["ls-files", "--error-unmatch", "--", rel])
    return code == 0


def prefix_token_match(actual: str, expected: str, *, version: bool = False) -> bool:
    """os 用词段匹配；python 用版本边界匹配（3.12 匹配 3.12.x，不匹配 3.120）。"""
    actual_l = actual.strip().lower()
    expected_l = expected.strip().lower()
    if not expected_l:
        return False
    if actual_l == expected_l:
        return True
    if version:
        if not actual_l.startswith(expected_l):
            return False
        rest = actual_l[len(expected_l):]
        return not rest or not rest[0].isdigit()
    index = actual_l.find(expected_l)
    while index != -1:
        before_ok = index == 0 or not actual_l[index - 1].isalnum()
        after = index + len(expected_l)
        after_ok = after == len(actual_l) or not actual_l[after].isalnum()
        if before_ok and after_ok:
            return True
        index = actual_l.find(expected_l, index + 1)
    return False


def repo_relative(root: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def git_sha(root: Path, rev: str) -> str | None:
    code, out, _ = git(root, ["rev-parse", "--verify", f"{rev}^{{commit}}"])
    return out.strip() if code == 0 and out.strip() else None


def changed_paths(root: Path, commit: str) -> list[str] | None:
    """证据 commit 之后的变化：已提交增量 + 未提交（含未跟踪）文件。"""
    if git_sha(root, commit) is None:
        return None
    changed: set[str] = set()
    # -z：非 ASCII 路径保持原样，不做 Git 转义（与 check_plan 的 K17 修复一致）。
    code, out, _ = git(root, ["diff", "-z", "--name-only", commit])
    if code == 0:
        changed.update(item.strip() for item in out.split("\0") if item.strip())
    code, out, _ = git(root, ["status", "--porcelain", "-z", "--untracked-files=all"])
    if code == 0:
        records = out.split("\0")
        index = 0
        while index < len(records):
            record = records[index]
            index += 1
            if len(record) < 4:
                continue
            status, path = record[:2], record[3:]
            if "R" in status or "C" in status:
                index += 1
            if "??" in status:
                changed.add(path.strip())
    return sorted(changed)


def glob_regex(pattern: str) -> re.Pattern[str]:
    """把常见 glob（** / * / ?）转成匹配仓库相对路径的正则。"""
    out = ["^"]
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    out.append("$")
    return re.compile("".join(out))


# ── 证据读取（当前 / 归档） ──────────────────────────────────────────────
def evidence_inventory(root: Path, config: dict) -> tuple[list[Path], list[Path]]:
    """递归扫描证据目录，返回 (当前证据, 归档证据)；路径含 `_archive` 段即归档。"""
    directory = config_path(root, config, "evidence")
    if not directory.is_dir():
        fail(f"证据目录不存在：{display(directory)}（先运行 harness-init 生成）")
    current: list[Path] = []
    archived: list[Path] = []
    for path in sorted(directory.rglob("*.json")):
        if not EVIDENCE_ID_RE.fullmatch(path.stem):
            continue
        relative_parts = path.relative_to(directory).parts
        if ARCHIVE_DIRNAME in relative_parts:
            archived.append(path)
        else:
            current.append(path)
    return current, archived


def load_doc(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def superseded_reason(archived_id: str, archived_doc: dict | None, current_docs: dict[str, dict]) -> str:
    """归档证据的取代关系：当前证据 supersedes / 归档证据 supersededBy；否则明示未声明。"""
    if archived_doc is not None:
        superseded_by = archived_doc.get("supersededBy")
        candidates: list[str] = []
        if isinstance(superseded_by, str):
            candidates = [superseded_by]
        elif isinstance(superseded_by, list):
            candidates = [str(item) for item in superseded_by]
        for candidate in candidates:
            if candidate in current_docs:
                return f"已被 {candidate} 取代"
    for current_id, current_doc in current_docs.items():
        if not isinstance(current_doc, dict):
            continue
        supersedes = current_doc.get("supersedes")
        declared: list[str] = []
        if isinstance(supersedes, str):
            declared = [supersedes]
        elif isinstance(supersedes, list):
            declared = [str(item) for item in supersedes]
        if archived_id in declared:
            return f"已被 {current_id} 取代"
    return "位于 _archive（未声明取代关系）"


# ── 三值判定 ─────────────────────────────────────────────────────────────
def dotted_get(document: object, dotted: str) -> object:
    current = document
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def git_is_ancestor(root: Path, commit: str) -> bool:
    """commit 是否为 HEAD 本身或其祖先（防止伪造/游离 commit 冒充完成）。"""
    code, _, _ = git(root, ["merge-base", "--is-ancestor", commit, "HEAD"])
    return code == 0


def artifact_paths(root: Path, doc: dict) -> tuple[list[str], list[str]]:
    """返回 (合法的仓库相对 artifact 路径, 问题列表)。

    契约：result.artifacts（数组）为规范字段；result.xcresultPath 作为 legacy 兼容。
    路径必须是仓库相对路径、不得含 `..`、文件/目录必须存在。
    """
    result = doc.get("result") if isinstance(doc.get("result"), dict) else {}
    raw: list[str] = []
    items = result.get("artifacts")
    if isinstance(items, list):
        raw.extend(item.strip() for item in items if isinstance(item, str) and item.strip())
    legacy = result.get("xcresultPath")
    if isinstance(legacy, str) and legacy.strip() and legacy.strip() not in raw:
        raw.append(legacy.strip())
    valid: list[str] = []
    problems: list[str] = []
    seen: set[str] = set()
    for rel in raw:
        if rel in seen:
            continue
        seen.add(rel)
        candidate = Path(rel)
        if candidate.is_absolute() or ".." in candidate.parts:
            problems.append(f"artifact 路径必须是仓库相对路径且不含 ..：{rel!r}")
            continue
        if not (root / candidate).exists():
            problems.append(f"artifact 不存在：{rel}")
            continue
        valid.append(rel)
    return valid, problems


def artifact_tracking_issues(root: Path, doc: dict) -> list[str]:
    """当前证据的每个 artifact 必须存在且被 git 跟踪（路径仍是仓库相对路径）。"""
    result = doc.get("result") if isinstance(doc.get("result"), dict) else {}
    raw: list[str] = []
    items = result.get("artifacts")
    if isinstance(items, list):
        raw.extend(item.strip() for item in items if isinstance(item, str) and item.strip())
    legacy = result.get("xcresultPath")
    if isinstance(legacy, str) and legacy.strip() and legacy.strip() not in raw:
        raw.append(legacy.strip())
    issues: list[str] = []
    seen: set[str] = set()
    for rel in raw:
        if rel in seen:
            continue
        seen.add(rel)
        candidate = Path(rel)
        if candidate.is_absolute() or ".." in candidate.parts:
            issues.append(f"artifact 路径必须是仓库相对路径：{rel!r}")
            continue
        if not (root / candidate).exists():
            issues.append(f"artifact 不存在：{rel}")
            continue
        if not git_tracked(root, rel):
            issues.append(f"artifact 未被 git 跟踪：{rel}")
    return issues


def recount_junit(root: Path, rel: str) -> tuple[tuple[int, int, int] | None, str]:
    """从 JUnit XML 独立重算 passed/failed/skipped；失败返回 (None, 原因)。"""
    script = Path(__file__).resolve().parent / "evidence_from_junit.py"
    if not script.is_file():
        return None, "缺 tools/evidence_from_junit.py，无法重算（test-count PASS 需要可重算 artifact）"
    try:
        spec = importlib.util.spec_from_file_location("_kit_evidence_from_junit", script)
        if spec is None or spec.loader is None:
            return None, "无法加载 tools/evidence_from_junit.py"
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module  # dataclass 需要模块已注册
        spec.loader.exec_module(module)
        element = ET.parse(root / rel).getroot()
        counts = module.aggregate(element)
    except (OSError, ET.ParseError) as exc:
        return None, f"JUnit XML 无法解析/读取：{rel}：{exc}"
    except Exception as exc:  # pragma: no cover - 防御（模块加载异常等）
        return None, f"JUnit 重算失败：{rel}：{exc}"
    passed = max(0, counts.tests - counts.failed - counts.skipped)
    return (passed, counts.failed, counts.skipped), ""


# ── E3：claim 环境模型 + skipped 容差 ────────────────────────────────────
def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def evidence_environment(doc: dict) -> dict:
    return doc.get("environment") if isinstance(doc.get("environment"), dict) else {}


def claim_environment_status(claim: dict, doc: dict) -> tuple[str, str]:
    """claim.environment 与证据 environment 的匹配；返回 ("ok"|"UNVERIFIED"|"FAIL", 原因)。"""
    spec = claim.get("environment")
    if spec is None:
        return "ok", ""
    if not isinstance(spec, dict):
        return "FAIL", "claim.environment 必须是 object（{id, requires[], os, python}）"
    evidence_env = evidence_environment(doc)
    problems: list[str] = []
    expected_id = spec.get("id")
    if expected_id is not None:
        if not isinstance(expected_id, str) or not expected_id.strip():
            return "FAIL", "claim.environment.id 必须是非空字符串"
        actual_id = evidence_env.get("id")
        if not isinstance(actual_id, str) or not actual_id.strip():
            problems.append(f"证据 environment 缺 id（claim 要求 {expected_id!r}）")
        elif actual_id != expected_id:
            problems.append(f"environment.id 不匹配（claim={expected_id!r}，证据={actual_id!r}）")
    requires_raw = spec.get("requires")
    if requires_raw is not None:
        if not isinstance(requires_raw, (list, str)):
            return "FAIL", "claim.environment.requires 必须是数组或逗号分隔字符串"
        required = as_list(requires_raw)
        provided = as_list(evidence_env.get("requires"))
        missing = [item for item in required if item not in provided]
        if missing:
            problems.append(f"environment.requires 未覆盖：缺 {missing}（证据 {provided or []}）")
    for key in ("os", "python"):
        expected = spec.get(key)
        if expected is None:
            continue
        if not isinstance(expected, str) or not expected.strip():
            return "FAIL", f"claim.environment.{key} 必须是非空字符串"
        actual = evidence_env.get(key)
        matched = isinstance(actual, str) and prefix_token_match(actual, expected, version=(key == "python"))
        if not matched:
            kind = "版本边界" if key == "python" else "词段"
            problems.append(f"environment.{key} 不匹配（要求 {expected}（{kind}匹配），证据 {actual!r}）")
    if problems:
        return "UNVERIFIED", "环境不匹配：" + "；".join(problems)
    return "ok", ""


def normalize_skip_value(value: object, label: str, max_range: int) -> tuple[dict | None, str, str]:
    """把 expectedSkipped 的具体值归一为 {kind:exact|range,...}；区间宽度受限。"""
    if isinstance(value, int) and not isinstance(value, bool):
        return {"kind": "exact", "value": value}, "", ""
    if isinstance(value, dict):
        minimum = value.get("min")
        maximum = value.get("max")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or not isinstance(maximum, int) or isinstance(maximum, bool):
            return None, "FAIL", f"{label} 区间需要整数 min/max：{value!r}"
        if minimum > maximum:
            return None, "FAIL", f"{label} 区间非法：min={minimum} > max={maximum}"
        width = maximum - minimum
        if width > max_range:
            return (
                None,
                "FAIL",
                f"{label} 区间过宽：max-min={width} > config.harden.maxSkippedRange="
                f"{max_range}，请收紧或按环境配置",
            )
        return {"kind": "range", "min": minimum, "max": maximum}, "", ""
    return None, "FAIL", f"{label} 配置非法：{value!r}（支持 int / {{min,max}} / {{byEnvironment}}）"


def resolve_expected_skipped(
    claim: dict, baseline: object, doc: dict, max_range: int
) -> tuple[dict | None, str, str]:
    """解析 expectedSkipped（字符串点号路径或 object），返回 (期望, 错误状态, 原因)。"""
    raw = claim.get("expectedSkipped")
    label = "claim.expectedSkipped"
    if isinstance(raw, str) and raw.strip():
        spec = dotted_get(baseline, raw)
        label = raw
        if spec is None:
            return None, "FAIL", f"baseline 缺少 {raw}"
    elif isinstance(raw, dict):
        spec = raw
    else:
        return None, "FAIL", "claim 未配置 expectedSkipped（点号路径或 object）"
    if isinstance(spec, dict) and "byEnvironment" in spec:
        mapping = spec.get("byEnvironment")
        if not isinstance(mapping, dict):
            return None, "FAIL", f"{label}.byEnvironment 必须是 object"
        if not mapping:
            return None, "FAIL", f"{label}.byEnvironment 不能为空"
        env_id = evidence_environment(doc).get("id")
        if not isinstance(env_id, str) or not env_id.strip():
            return None, "UNVERIFIED", f"{label}.byEnvironment 需要证据 environment.id，但证据未声明"
        if env_id not in mapping:
            available = "、".join(sorted(str(key) for key in mapping))
            return None, "UNVERIFIED", f"{label}.byEnvironment 未定义环境 {env_id!r}（可用：{available}）"
        return normalize_skip_value(mapping[env_id], f"{label}.byEnvironment[{env_id}]", max_range)
    return normalize_skip_value(spec, label, max_range)


def skipped_verdict(expectation: dict, skipped: int, label: str) -> tuple[str, str]:
    if expectation["kind"] == "exact":
        expected = expectation["value"]
        if skipped != expected:
            return "FAIL", f"skipped={skipped} != {label}={expected}"
        return "", f"skipped={skipped}=={label}"
    minimum = expectation["min"]
    maximum = expectation["max"]
    if not minimum <= skipped <= maximum:
        return "FAIL", f"skipped={skipped} 不在 [{minimum},{maximum}]"
    return "", f"skipped={skipped} in [{minimum},{maximum}]"


def evaluate_test_count(root: Path, config: dict, claim: dict, doc: dict) -> tuple[str, str]:
    baseline_rel = claim.get("baseline")
    floor_key = claim.get("floor")
    raw_skipped = claim.get("expectedSkipped")
    has_skipped_config = (isinstance(raw_skipped, str) and raw_skipped.strip()) or isinstance(raw_skipped, dict)
    if not isinstance(baseline_rel, str) or not baseline_rel:
        return "FAIL", "claim 未配置 baseline（test-count 需要 baseline/floor/expectedSkipped）"
    if not isinstance(floor_key, str) or not floor_key:
        return "FAIL", "claim 未配置 floor（点号路径，如 unit.floor）"
    if not has_skipped_config:
        return "FAIL", "claim 未配置 expectedSkipped（点号路径或 object）"
    baseline_path = root / baseline_rel
    if not baseline_path.is_file():
        return "FAIL", f"baseline 不存在：{baseline_rel}"
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "FAIL", f"baseline 无法解析：{baseline_rel}：{exc}"
    floor = dotted_get(baseline, floor_key)
    if not isinstance(floor, int) or isinstance(floor, bool):
        return "FAIL", f"baseline 缺少整数 {floor_key}"
    harden = config.get("harden") if isinstance(config.get("harden"), dict) else {}
    max_skipped_range = harden.get("maxSkippedRange", 5)
    if not isinstance(max_skipped_range, int) or isinstance(max_skipped_range, bool) or max_skipped_range < 0:
        return "FAIL", "config.harden.maxSkippedRange 必须是 >=0 的整数"

    # E3.1：claim 环境声明先于计数校验；环境不满足是 UNVERIFIED（不是代码回归）。
    env_status, env_reason = claim_environment_status(claim, doc)
    if env_status != "ok":
        return env_status, env_reason

    # E3.4：按环境选择 floor（未配置 floorByEnvironment 时沿用 floor）。
    floor_by_env = claim.get("floorByEnvironment")
    if floor_by_env is not None:
        if not isinstance(floor_by_env, dict) or not floor_by_env:
            return "FAIL", "claim.floorByEnvironment 必须是非空 object（环境→整数 floor）"
        env_id = evidence_environment(doc).get("id")
        if not isinstance(env_id, str) or not env_id.strip():
            return "UNVERIFIED", "claim.floorByEnvironment 需要证据 environment.id，但证据未声明"
        if env_id not in floor_by_env:
            available = "、".join(sorted(str(key) for key in floor_by_env))
            return "UNVERIFIED", f"claim.floorByEnvironment 未定义环境 {env_id!r}（可用：{available}）"
        selected = floor_by_env[env_id]
        if not isinstance(selected, int) or isinstance(selected, bool):
            return "FAIL", f"claim.floorByEnvironment[{env_id}] 必须是整数：{selected!r}"
        floor = selected

    # provenance：PASS 证据必须来自 clean tree，且 commit 可解析、是 HEAD 祖先。
    git_meta = doc.get("git") if isinstance(doc.get("git"), dict) else {}
    commit = str(git_meta.get("commit") or "").strip().lower()
    if not commit:
        return "FAIL", "证据缺 git.commit，无法确认 provenance"
    if git_sha(root, commit) is None:
        return "FAIL", f"git.commit 无法解析：{commit}"
    if not git_is_ancestor(root, commit):
        return "FAIL", f"git.commit 不是 HEAD 或其祖先：{commit}"
    if git_meta.get("dirty") is not False:
        return "FAIL", "verdict=PASS 但 git.dirty 非 false（dirty 证据不可判 PASS）"

    result = doc.get("result") if isinstance(doc.get("result"), dict) else {}
    counts = {key: result.get(key) for key in ("passed", "failed", "skipped")}
    if any(not isinstance(value, int) or isinstance(value, bool) for value in counts.values()):
        return "FAIL", "result.passed/failed/skipped 需为整数"
    require_artifact = claim.get("requireArtifact", True) is not False
    artifacts, problems = artifact_paths(root, doc)
    if problems:
        return "FAIL", "；".join(problems)
    if not artifacts:
        if require_artifact:
            return (
                "UNVERIFIED",
                "缺可重算 artifact（claim.requireArtifact 默认 true；用 tools/evidence_from_junit.py 生成 JUnit XML 后重试）",
            )
        # 显式 opt-out 的 legacy claim：仍在 provenance 通过后接受自报 counts，但注明未重算。
        passed, failed, skipped = counts["passed"], counts["failed"], counts["skipped"]
        note = "；未重算（claim.requireArtifact=false，legacy）"
    else:
        xml_artifacts = [rel for rel in artifacts if rel.lower().endswith(".xml")]
        if not xml_artifacts:
            if require_artifact:
                return "UNVERIFIED", "artifact 无法独立重算（需要 JUnit XML；xcresult 请先转换为 JUnit）"
            passed, failed, skipped = counts["passed"], counts["failed"], counts["skipped"]
            note = "；未重算（非 XML artifact 且 claim.requireArtifact=false）"
        else:
            totals = [0, 0, 0]
            for rel in xml_artifacts:
                recounted, reason = recount_junit(root, rel)
                if recounted is None:
                    return "FAIL", reason
                totals[0] += recounted[0]
                totals[1] += recounted[1]
                totals[2] += recounted[2]
            passed, failed, skipped = totals
            claimed = (counts["passed"], counts["failed"], counts["skipped"])
            if claimed != (passed, failed, skipped):
                return (
                    "FAIL",
                    "证据自报 counts 与 artifact 重算不一致："
                    f"自报={claimed} / 重算={(passed, failed, skipped)}",
                )
            note = f"；已从 {len(xml_artifacts)} 个 JUnit XML 重算"
    if failed != 0:
        return "FAIL", f"failed={failed}（要求 0）"
    if passed < floor:
        return "FAIL", f"passed={passed} < {floor_key}={floor}"

    expectation, skip_status, skip_reason = resolve_expected_skipped(
        claim, baseline, doc, max_skipped_range
    )
    if expectation is None:
        return skip_status or "FAIL", skip_reason
    label = raw_skipped if isinstance(raw_skipped, str) else "expectedSkipped"
    compare_verdict, compare_reason = skipped_verdict(expectation, skipped, label)
    if compare_verdict:
        return compare_verdict, compare_reason
    return (
        "PASS",
        f"passed={passed}≥{floor_key}={floor}，failed=0，{compare_reason}{note}",
    )


def evaluate_static(root: Path, config: dict, claim: dict, doc: dict) -> tuple[str, str]:
    command = claim.get("command")
    if not isinstance(command, str) or not command.strip():
        return "UNVERIFIED", "claim 未配置 command，无法复跑静态检查"
    try:
        result = subprocess.run(
            command, shell=True, cwd=str(root), capture_output=True, text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "UNVERIFIED", f"command 无法执行：{exc}"
    if result.returncode == 0:
        return "PASS", f"command exit 0：{command}"
    tail = [line.strip() for line in (result.stderr or result.stdout).splitlines() if line.strip()]
    detail = f"（{tail[-1][:120]}）" if tail else ""
    return "FAIL", f"command exit {result.returncode}：{command}{detail}"


# ── freshness ────────────────────────────────────────────────────────────
PROCESS_PATH_KEYS = ("evidence", "plans", "reviews")


def _process_prefixes(config: dict) -> tuple[str, ...]:
    """状态/过程目录（evidence/plans/reviews）的变更不应让 claim 失效。"""
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    prefixes = []
    for key in PROCESS_PATH_KEYS:
        value = paths.get(key)
        if isinstance(value, str) and value.strip():
            prefixes.append(value.strip().rstrip("/"))
    return tuple(prefixes)


def _is_process_path(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


def stale_files(root: Path, config: dict, claim_name: str, commit: object) -> list[str] | None:
    patterns = (config.get("freshness") or {}).get(claim_name)
    if not isinstance(patterns, list) or not patterns:
        return []
    if not isinstance(commit, str) or not commit.strip():
        return ["<证据缺 git.commit>"]
    changed = changed_paths(root, commit.strip().lower())
    if changed is None:
        return [f"<证据 commit 无法解析：{commit}>"]
    prefixes = _process_prefixes(config)
    changed = [path for path in changed if not _is_process_path(path, prefixes)]
    regexes = [glob_regex(pattern) for pattern in patterns if isinstance(pattern, str)]
    return [path for path in changed if any(regex.match(path) for regex in regexes)]


# ── 单个证据判定 ─────────────────────────────────────────────────────────
def verify_one(
    root: Path,
    config: dict,
    path: Path,
    fresh: bool,
    strict: bool,
    *,
    repo_available: bool,
    allow_untracked: bool,
) -> tuple[str, str]:
    evidence_id = path.stem
    doc = load_doc(path)
    if doc is None:
        return "FAIL", "证据 JSON 无法解析或不是 object"
    claim_name = doc.get("claim")
    claim = next(
        (item for item in config.get("claims", []) if isinstance(item, dict) and item.get("name") == claim_name),
        None,
    )
    if claim is None:
        return "FAIL", f"claim 未在 config.claims 声明：{claim_name!r}"
    recorded = doc.get("verdict")
    if recorded not in VERDICTS:
        return "FAIL", f"证据 verdict 非法：{recorded!r}"
    claim_type = claim.get("type")
    if recorded == "FAIL":
        verdict, reason = "FAIL", "证据 verdict=FAIL"
    elif recorded == "UNVERIFIED":
        verdict, reason = "UNVERIFIED", "证据 verdict=UNVERIFIED"
    else:
        if claim_type == "test-count":
            verdict, reason = evaluate_test_count(root, config, claim, doc)
        elif claim_type == "static":
            verdict, reason = evaluate_static(root, config, claim, doc)
        else:
            verdict, reason = "FAIL", f"claim type 非 test-count|static：{claim_type!r}"

    # E1.4 / E3.5：当前证据必须被 git 跟踪；--strict 下 --allow-untracked 无效。
    effective_allow = allow_untracked and not strict
    if repo_available:
        rel = repo_relative(root, path)
        if rel is None or not git_tracked(root, rel):
            if effective_allow:
                print(f"[WARN] CLAIM {evidence_id}: {UNTRACKED_NOTE}（--allow-untracked 显式放行）")
            elif verdict == "PASS":
                verdict, reason = "UNVERIFIED", f"{reason}；{UNTRACKED_NOTE}"
            else:
                reason = f"{reason}；{UNTRACKED_NOTE}"
        # E1.3：当前证据引用的每个 artifact 也必须被 git 跟踪且存在。
        artifact_issues = artifact_tracking_issues(root, doc)
        if artifact_issues:
            artifact_note = "；" + "；".join(artifact_issues) + "（CI 无法复核）"
            if effective_allow:
                print(f"[WARN] CLAIM {evidence_id}: artifact 未被 git 跟踪（--allow-untracked 显式放行）")
            else:
                verdict, reason = "UNVERIFIED", f"{reason}{artifact_note}"

    # E3.3：static claim 每次重跑命令，freshness 不适用（不做 STALE 判定/降级）。
    if fresh:
        if claim_type == "static":
            note = "；static claim 复跑通过，freshness 不适用" if verdict == "PASS" else "；static claim 复跑（freshness 不适用）"
            reason = f"{reason}{note}"
        else:
            git_meta = doc.get("git") if isinstance(doc.get("git"), dict) else {}
            stale = stale_files(root, config, claim_name, git_meta.get("commit"))
            if stale:
                preview = "、".join(stale[:3]) + ("…" if len(stale) > 3 else "")
                note = f"STALE：证据 commit 之后有相关变更（{preview}）"
                if strict and verdict == "PASS":
                    verdict, reason = "UNVERIFIED", f"{reason}；{note}（--strict 降级）"
                else:
                    suffix = "（未加 --strict，不降级）" if verdict == "PASS" else ""
                    reason = f"{reason}；{note}{suffix}"
    return verdict, reason


def archived_takeover(archived_id: str, archived_doc: dict | None, current_docs: dict[str, dict]) -> str | None:
    """归档 FAIL/UNVERIFIED 是否被合法接管：当前 PASS、claim 相同、非自环、supersedes 含该 id。"""
    if not isinstance(archived_doc, dict):
        return None
    archived_claim = archived_doc.get("claim")
    for current_id, current_doc in current_docs.items():
        if current_id == archived_id or not isinstance(current_doc, dict):
            continue
        if current_doc.get("verdict") != "PASS":
            continue
        if current_doc.get("claim") != archived_claim:
            continue
        supersedes = current_doc.get("supersedes")
        if isinstance(supersedes, str):
            declared = [supersedes]
        elif isinstance(supersedes, list):
            declared = [str(item) for item in supersedes]
        else:
            declared = []
        if archived_id in declared:
            return current_id
    return None


def required_claim_names(config: dict) -> list[str]:
    """config.claims 中 required 未显式 false 的 claim 名称。"""
    names: list[str] = []
    for claim in config.get("claims", []):
        if not isinstance(claim, dict):
            continue
        name = claim.get("name")
        if not isinstance(name, str) or not name:
            continue
        if claim.get("required", True) is not False:
            names.append(name)
    return names


def emit_archived_lines(archived_records: list[tuple[Path, dict | None]], current_docs: dict[str, dict]) -> int:
    """打印归档证据行，返回“未被合法取代的 FAIL/UNVERIFIED”个数（参与聚合）。"""
    unverified = 0
    for path, doc in archived_records:
        archived_id = path.stem
        takeover = archived_takeover(archived_id, doc, current_docs)
        archived_verdict = doc.get("verdict") if isinstance(doc, dict) else None
        if takeover is not None:
            print(f"CLAIM {archived_id}: SUPERSEDED — 已被 {takeover} 取代")
        elif archived_verdict in ("FAIL", "UNVERIFIED"):
            print(
                f"CLAIM {archived_id}: UNVERIFIED — 归档{archived_verdict}证据未被合法取代"
                "（需当前 PASS 证据 supersedes 该 id 且 claim 相同）"
            )
            unverified += 1
        else:
            reason = superseded_reason(archived_id, doc, current_docs)
            print(f"CLAIM {archived_id}: SUPERSEDED — {reason}")
    return unverified


def main(argv: list[str]) -> int:
    root, args = parse_cli(argv)
    if args and args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    allowed_flags = ("--all", "--fresh", "--strict", "--allow-untracked")
    flags = set(args)
    unknown = [item for item in args if item not in allowed_flags]
    if unknown:
        fail(
            "用法：verify_claim.py --all [--fresh] [--strict] [--allow-untracked] [--root PATH]"
            f"（未知参数：{' '.join(unknown)}）",
            2,
        )
    if "--all" not in flags:
        fail("用法：verify_claim.py --all [--fresh] [--strict] [--allow-untracked] [--root PATH]", 2)
    config = load_config(root)
    fresh = "--fresh" in flags
    strict = "--strict" in flags
    allow_untracked = "--allow-untracked" in flags
    if strict:
        fresh = True
    current, archived = evidence_inventory(root, config)
    print(
        f"验证 {len(current)} 条当前证据（fresh={str(fresh).lower()}）；"
        f"归档 {len(archived)} 条（只列出，不参与判定）"
    )
    repo_available = git_is_repo(root)
    if not repo_available:
        print("[WARN] 非 git 仓库：跳过证据文件 tracked 校验（无法确认 CI 可复核）")
    current_docs = {path.stem: load_doc(path) for path in current}
    archived_records = [(path, load_doc(path)) for path in archived]
    current_claim_names = {
        doc["claim"] for doc in current_docs.values()
        if isinstance(doc, dict) and isinstance(doc.get("claim"), str)
    }
    missing_required = [name for name in required_claim_names(config) if name not in current_claim_names]

    def emit_missing_required() -> int:
        for name in missing_required:
            print(f"CLAIM {name}: UNVERIFIED — 缺少当前证据（config.claims.required）")
        return len(missing_required)

    if not current:
        emit_archived_lines(archived_records, current_docs)
        if archived_records:
            print(
                "CLAIM <none>: UNVERIFIED — 未找到当前证据"
                "（只有 `_archive` 归档证据；归档不参与三值判定）"
            )
        else:
            print("CLAIM <none>: UNVERIFIED — 未找到证据文件（no evidence under config.paths.evidence）")
        emit_missing_required()
        return 2

    failures = 0
    current_unverified = 0
    for path in current:
        verdict, reason = verify_one(
            root, config, path, fresh, strict,
            repo_available=repo_available, allow_untracked=allow_untracked,
        )
        print(f"CLAIM {path.stem}: {verdict} — {reason}")
        if verdict == "FAIL":
            failures += 1
        elif verdict == "UNVERIFIED":
            current_unverified += 1
    archived_unverified = emit_archived_lines(archived_records, current_docs)
    missing_unverified = emit_missing_required()
    unverified = current_unverified + archived_unverified + missing_unverified
    passed = max(0, len(current) - failures - current_unverified)
    if failures:
        print(f"结论：FAIL（{passed} PASS / {failures} FAIL / {unverified} UNVERIFIED）")
        return 1
    if unverified:
        print(f"结论：UNVERIFIED（{passed} PASS / {failures} FAIL / {unverified} UNVERIFIED）")
        return 2
    print(f"结论：PASS（{passed} PASS / 0 FAIL / 0 UNVERIFIED）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
