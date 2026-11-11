#!/usr/bin/env python3
"""harness-kit 通用证据三值判定（标准库；无第三方依赖；不联网）。

用法（脚本被 init 复制到目标项目 tools/ 下）：
  python3 tools/verify_claim.py --all [--fresh] [--strict] [--root PATH]

根目录 = 脚本上级目录（tools/ 的父目录）；--root 可覆盖。配置唯一来源
<root>/harness/config.json；证据在 config.paths.evidence 下，claim 定义见
config.claims（type=test-count|static）。

每个证据输出固定一行：
  CLAIM <evidence-id>: PASS|FAIL|UNVERIFIED — <原因>

判定规则：
  - 证据 verdict=FAIL → FAIL；verdict=UNVERIFIED → UNVERIFIED；verdict 非法 → FAIL。
  - verdict=PASS 时按 claim 类型复核：
    * test-count：读 claim.baseline + claim.floor / claim.expectedSkipped（点号路径）。
      provenance：git.commit 必须可解析且是 HEAD 或其祖先，git.dirty 必须为 false。
      artifact：result.artifacts（数组；result.xcresultPath 为 legacy 兼容）必须存在；
      claim.requireArtifact 缺省为 **true**（显式 false 仅用于 legacy opt-out）；
      有 JUnit XML artifact 时从 XML 独立重算 passed/failed/skipped，与自报值不一致 → FAIL；
      无 artifact 或只有非 XML artifact（xcresult 等）→ UNVERIFIED（无法独立重算）。
      再要求 failed==0、passed>=floor、skipped==expectedSkipped。
    * static：复跑 claim.command；exit 0 → PASS，非 0 → FAIL，command 缺失 → UNVERIFIED。
  - --fresh 按 config.freshness[claim] 的 glob 比较 evidence.git.commit 与当前工作树
    （含已提交增量、未提交与未跟踪文件）；有相关变更即 STALE。--strict 隐含 --fresh，
    且 STALE 的 PASS 降级为 UNVERIFIED；不加 --strict 时保留 PASS 并在原因里标注 STALE。
  - 没有证据文件 → 输出 UNVERIFIED 语义（exit 2），避免“空证据”被当全绿。

聚合退出码：任一 FAIL → 1；否则任一 UNVERIFIED → 2；全 PASS → 0。
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


def git_sha(root: Path, rev: str) -> str | None:
    code, out, _ = git(root, ["rev-parse", "--verify", f"{rev}^{{commit}}"])
    return out.strip() if code == 0 and out.strip() else None


def changed_paths(root: Path, commit: str) -> list[str] | None:
    """证据 commit 之后的变化：已提交增量 + 未提交（含未跟踪）文件。"""
    if git_sha(root, commit) is None:
        return None
    changed: set[str] = set()
    code, out, _ = git(root, ["diff", "--name-only", commit])
    if code == 0:
        changed.update(line.strip() for line in out.splitlines() if line.strip())
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


# ── 证据读取 ─────────────────────────────────────────────────────────────
def evidence_files(root: Path, config: dict) -> list[Path]:
    directory = config_path(root, config, "evidence")
    if not directory.is_dir():
        fail(f"证据目录不存在：{display(directory)}（先运行 harness-init 生成）")
    return sorted(
        path for path in directory.glob("*.json") if EVIDENCE_ID_RE.fullmatch(path.stem)
    )


def load_doc(path: Path) -> dict | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


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


def evaluate_test_count(root: Path, config: dict, claim: dict, doc: dict) -> tuple[str, str]:
    baseline_rel = claim.get("baseline")
    floor_key = claim.get("floor")
    skipped_key = claim.get("expectedSkipped")
    if not isinstance(baseline_rel, str) or not baseline_rel:
        return "FAIL", "claim 未配置 baseline（test-count 需要 baseline/floor/expectedSkipped）"
    if not isinstance(floor_key, str) or not floor_key:
        return "FAIL", "claim 未配置 floor（点号路径，如 unit.floor）"
    if not isinstance(skipped_key, str) or not skipped_key:
        return "FAIL", "claim 未配置 expectedSkipped（点号路径，如 unit.expectedSkipped）"
    baseline_path = root / baseline_rel
    if not baseline_path.is_file():
        return "FAIL", f"baseline 不存在：{baseline_rel}"
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "FAIL", f"baseline 无法解析：{baseline_rel}：{exc}"
    floor = dotted_get(baseline, floor_key)
    expected = dotted_get(baseline, skipped_key)
    if not isinstance(floor, int) or isinstance(floor, bool) or not isinstance(expected, int) or isinstance(expected, bool):
        return "FAIL", f"baseline 缺少整数 {floor_key}/{skipped_key}"

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
    if skipped != expected:
        return "FAIL", f"skipped={skipped} != {skipped_key}={expected}"
    return "PASS", f"passed={passed}≥{floor_key}={floor}，failed=0，skipped={skipped}=={skipped_key}{note}"


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


def verify_one(root: Path, config: dict, path: Path, fresh: bool, strict: bool) -> tuple[str, str]:
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
    if recorded == "FAIL":
        verdict, reason = "FAIL", "证据 verdict=FAIL"
    elif recorded == "UNVERIFIED":
        verdict, reason = "UNVERIFIED", "证据 verdict=UNVERIFIED"
    else:
        claim_type = claim.get("type")
        if claim_type == "test-count":
            verdict, reason = evaluate_test_count(root, config, claim, doc)
        elif claim_type == "static":
            verdict, reason = evaluate_static(root, config, claim, doc)
        else:
            verdict, reason = "FAIL", f"claim type 非 test-count|static：{claim_type!r}"
    if fresh:
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


def main(argv: list[str]) -> int:
    root, args = parse_cli(argv)
    if args and args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    flags = set(args)
    unknown = [item for item in args if item not in ("--all", "--fresh", "--strict")]
    if unknown:
        fail(f"用法：verify_claim.py --all [--fresh] [--strict] [--root PATH]（未知参数：{' '.join(unknown)}）", 2)
    if "--all" not in flags:
        fail("用法：verify_claim.py --all [--fresh] [--strict] [--root PATH]", 2)
    config = load_config(root)
    fresh = "--fresh" in flags
    strict = "--strict" in flags
    if strict:
        fresh = True
    files = evidence_files(root, config)
    print(f"验证 {len(files)} 条证据（fresh={str(fresh).lower()}，strict={str(strict).lower()}）")
    if not files:
        print("CLAIM <none>: UNVERIFIED — 未找到证据文件（no evidence under config.paths.evidence）")
        return 2
    failures = 0
    unverified = 0
    for path in files:
        verdict, reason = verify_one(root, config, path, fresh, strict)
        print(f"CLAIM {path.stem}: {verdict} — {reason}")
        if verdict == "FAIL":
            failures += 1
        elif verdict == "UNVERIFIED":
            unverified += 1
    passed = len(files) - failures - unverified
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
